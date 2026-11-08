# matisse GPU：以三个上游仓库为准的重审（2026-11-08）

本文的每一条事实都来自下面三个仓库的**当前源码**，不引用本项目此前的结论。
凡是本项目自己测出来的东西，都单独标注为"设备实测"。

| 仓库 | 取用内容 | 取用方式 |
|---|---|---|
| `torvalds/linux` `drivers/gpu/drm/panthor` | `panthor_hw.c/h` `panthor_gpu.c` `panthor_gpu_regs.h` `panthor_mmu_regs.h` `panthor_fw.c/h` `panthor_fw_regs.h` `panthor_mmu.c` | `raw.githubusercontent.com/.../master/...`，2026-11-08 抓取 |
| `MiCode/Xiaomi_Kernel_OpenSource` 分支 `rubens-s-oss` | `drivers/gpu/mediatek/gpu_mali/mali_valhall/mali-r32p1/.../platform/mt6983/*`、`.../gpufreq/v2/gpufreq_mt6983.c`、`.../backend/gpu/mali_kbase_l2_mmu_config.c`、`.../protected_memory_allocator` | `git clone --depth 1 --filter=blob:none` + `git show HEAD:<path>` |
| `OnePlusOSS/android_kernel_5.10_oneplus_mt6983` | 同代 MT6983 平台胶水（用于交叉验证 MTK 平台层） | 见 §7 |

---

## 1. 这颗 GPU 是什么，panthor 会走哪条代码路径

`GPU_ID = 0xa8620004`。

```
GPU_ARCH_MAJOR(x) = x >> 28              -> 0xa  = 10
GPU_PROD_MAJOR(x) = (x & GENMASK(19,16)) >> 16 -> 0x2  = 2
```

`panthor_hw.c: GPU_PROD_ID_MAKE(10, 2) -> "Mali-G710"`，而
`panthor_hw_match[]` 把 arch 10..13 绑定到 `panthor_hw_arch_v10`：

```c
static struct panthor_hw panthor_hw_arch_v10 = {
	.ops = {
		.soft_reset    = panthor_gpu_soft_reset,
		.l2_power_off  = panthor_gpu_l2_power_off,
		.l2_power_on   = panthor_gpu_l2_power_on,
	},
};
```

arch 14 才改用独立的 `PWR_*` 寄存器块（`PWR_CONTROL_BASE` / `PWR_L2_PRESENT` /
`panthor_pwr_l2_power_on`）。**所以本机必须用 `GPU_CONTROL` 里的那一套
（`L2_PRESENT 0x120` / `L2_READY 0x160` / `L2_PWRON 0x1a0` / `L2_PWRTRANS 0x220`），
shim 目前用的正是这一套，选路正确。**厂商 DT 里的第五个中断 `PWR` 是 MTK 的
电源状态中断，不是 arch-14 的 PWR 块。

## 2. 寄存器语义（全部来自 panthor 头文件，逐位核对）

`panthor_gpu_regs.h`：

```
GPU_INT_BASE 0x20      GPU_IRQ_RESET_COMPLETED      BIT(8)
                       GPU_IRQ_POWER_CHANGED        BIT(9)
                       GPU_IRQ_POWER_CHANGED_ALL    BIT(10)
                       GPU_IRQ_CLEAN_CACHES_COMPLETED BIT(17)
                       GPU_IRQ_DOORBELL_MIRROR      BIT(18)
                       GPU_IRQ_MCU_STATUS_CHANGED   BIT(19)
GPU_CMD 0x30           GPU_SOFT_RESET = GPU_CMD_DEF(1,1) = 0x101
GPU_STATUS 0x34        ACTIVE BIT(0) PWR_ACTIVE BIT(1) PAGE_FAULT BIT(4)
                       PROTM_ACTIVE BIT(7) DBG_ENABLED BIT(8)
```

`panthor_fw_regs.h`：

```
MCU_CONTROL 0x700  ENABLE 1 AUTO 2 DISABLE 0
MCU_STATUS  0x704  DISABLED 0 ENABLED 1 HALT 2 FATAL 3
JOB_INT_BASE 0x1000  JOB_INT_GLOBAL_IF BIT(31)
CSF_DOORBELL(i) = 0x80000 + i*0x10000
```

`panthor_mmu_regs.h`：

```
AS_COMMAND 0x2428  NOP 0 UPDATE 1 LOCK 2 UNLOCK 3 FLUSH_PT 4 FLUSH_MEM 5
AS_TRANSCFG 0x2430 ADRMODE_AARCH64_4K (6<<0) · INA_BITS(x) (x<<6)
                   OUTA_BITS(x) (x<<14) · PTW_MEMATTR_WB (2<<24)
                   PTW_SH_OS (2<<28) · PTW_RA BIT(30)
```

用这张表核对 2407 记录的值：

- `AS_TRANSCFG = 0x42000006` = `AARCH64_4K | PTW_MEMATTR_WB | PTW_RA | INA_BITS(0)`。
  panthor 自己写 `INA_BITS(55 - va_bits)`（va_bits=48 → 7）并加 `PTW_SH_OS`。
  本机厂商 KMD 钉的是 `0x42000006`，而 shim 两种 INA 都飞过（`vendor_ina0`
  开关），**两种都撞同一面墙**，所以这不是变量。
- `GPU_STATUS = 0x100` 在**事务开始前**就读到，即 **`DBG_ENABLED` 一直是 1**，
  同时 `INT_RAWSTAT = 0x100` 说明 `RESET_COMPLETED` 是**上一轮遗留的未清位**。
  2407 结束时 `GPU_STATUS = 0x101`（`DBG_ENABLED|ACTIVE`），
  `reset_completed = 0`：**这次 SOFT_RESET 根本没完成**。

## 3. 上电：MT6983 的真实结构

`gpufreq/v2/gpufreq_mt6983.c: __gpufreq_power_control()` 的 POWER_ON 顺序是

```
AOC -> Buck -> MTCMOS -> Clock -> 恢复 MFG 寄存器 -> PDCv2 -> ACP -> HWDCM
    -> GPM -> SLC policy
```

`__gpufreq_mtcmos_control()` 里 `pd_mfg1` … `pd_mfg9`（注释写 "manually control
MFG2-18 if PDC is disabled"），也就是说 **GPU 被切成十几个 MTCMOS 子域**；
`GPUFREQ_PDCv2_ENABLE` 打开时改为"**让 GPU 侧自己控制 MTCMOS**"，即由
`GPU_CONTROL` 的 PWRON/PWRTRANS/PWRACTIVE 握手驱动 PDC 硬件。

这与 panthor 的模型完全一致，也是 shim 现在的做法：

```c
/* panthor_gpu.c:465 */
/* Resume the IRQ handler and power-on the L2-cache.
 * The FW takes care of powering the other blocks. */
```

**结论：shader/tiler 域不上电是设计如此，不是缺陷。** shim 只写 `L2_PWRON=1`
并等 `L2_READY.bit0`，与 `panthor_gpu_power_on(ptdev, L2, 1, 20000)` 逐位相同
（`l2_present=1`，所以 mask=1 也对）。设备实测 `l2_ready=1`，这一步是通的。

## 4. MCU 启动：panthor 的完整流程 vs shim

`panthor_fw.c` 的启动链路（arch v10）：

| # | panthor | shim | 一致？ |
|---|---|---|---|
| 1 | 设备复位：`GPU_CMD=GPU_SOFT_RESET`，清 `INT_CLEAR` bit8，等 `RESET_COMPLETED` | **事务里没有**，只在 cleanup 里做 | **否** |
| 2 | `GPU_COHERENCY_PROTOCOL=0x304` 在 L2 上电**之前**写 | 是（`0x304 <- 31`） | 是 |
| 3 | `L2_PWRON=1`，等 `L2_READY` | 是 | 是 |
| 4 | `AS_COMMAND=LOCK` | 是 | 是 |
| 5 | `AS_TRANSTAB`/`AS_MEMATTR`/`AS_TRANSCFG` + `AS_COMMAND=UPDATE` | 是（`0x2400/08/30` + cmd 1） | 是 |
| 6 | `JOB_INT_MASK = ~0`，`INT_CLEAR=GLOBAL_IF` | 是 | 是 |
| 7 | `MCU_CONTROL = MCU_CONTROL_AUTO (2)` | 是 | 是 |
| 8 | 等 `INT_STAT & JOB_INT_GLOBAL_IF`（1000 ms） | 轮询 `JOB_INT_RAWSTAT.bit31` | 是 |
| 9 | `panthor_fw_init_ifaces()`：`version != 0`、`input_va`/`output_va` 在 shared 内、`group_num` | 是（`stage=IFACE` 的全部条件） | 是 |
| 10 | `panthor_fw_init_global_iface()`：`core_en_mask`、三个 timer、`ack_irq_mask`、`toggle_reqs(ALLOC_EN|POWEROFF|PROGRESS)`、`doorbell` | `csf_global_init()` 同结构（2381 起） | 基本是 |

**唯一实质差异是第 1 步：panthor 在重置/恢复路径上一定先做一次成功的软复位
再碰 AS/MCU；shim 从不做，而且 2407 证明它做的复位也没完成。** 这里必须说准确：
`panthor_device_init()` 的冷启动路径（`panthor_mmu_init` → `panthor_fw_init`）
**不**复位，它信任 bootloader；复位出现在
`panthor_device_reset_work()`（`fw_pre_reset → mmu_pre_reset →
hw_soft_reset → l2_power_on → mmu_post_reset → fw_post_reset`）和
`panthor_device_resume()` 经 `panthor_gpu_suspend()` 走的同一条路上。
所以"先复位"是 panthor 的**重置语义**，不是它的冷启动不变式；把它当不变式引用
会高估这条证据的分量。2408 仍然值得做，只是它的依据是"厂商 KMD 在 device init
里就复位"加上"我们这颗 GPU 从没被这条路径复位过"，而不是"参考驱动总是这样"。
设备实测 `DBG_ENABLED` 常驻、`RESET_COMPLETED` 是陈旧的未清位，这两件事放在
一起只有两种解释：(a) GPU 被上一级（LK/GPUEB）留在 debug/halt 态；
(b) 复位根本没有真正跑完。**这两件事都必须先测清楚，否则"MCU 不启动"随时可能
是复位状态的后果而不是 bit 9 的后果。**

## 5. 固件加载：panthor 的地址约定

`panthor_fw.c`：`CSF_MCU_SHARED_REGION_START = 0x04000000`，
`CSF_MCU_SHARED_REGION_SIZE = 0x04000000`；每个 section 用**固件自己声明的
VA**（`hdr.va.start`）建 BO 并映射，`va` 必须按 **VM 页大小**对齐
（`panthor_vm_page_size(ptdev->fw->vm)`），并且

```c
if (!(hdr.flags & CSF_FW_BINARY_IFACE_ENTRY_WR))
	vm_map_flags |= DRM_PANTHOR_VM_BIND_OP_MAP_READONLY;
if (!(hdr.flags & CSF_FW_BINARY_IFACE_ENTRY_EX))
	vm_map_flags |= DRM_PANTHOR_VM_BIND_OP_MAP_NOEXEC;
if (cache_mode != CSF_FW_BINARY_IFACE_ENTRY_CACHE_MODE_CACHED)
	vm_map_flags |= DRM_PANTHOR_VM_BIND_OP_MAP_UNCACHED;
```

也就是**属性来自固件头，不是全局统一的一档**。本项目的 shim 是按镜像自己的
section 表映射的（`0x01000000` R-X、`0x02000000` RW、`0x02800000`、
`0x04000000` shared），与这一层一致；2403 已经用读回字 `0x0f10f857` 验证过。

## 6. 厂商侧多出来的、panthor 没有的东西

1. **`arm,physical-memory-group-manager`（MGM）**：DT 里
   `mali { physical-memory-group-manager = <&mgm>; }`，`mgm` 是
   `compatible = "arm,physical-memory-group-manager"` 的空节点。
   这是 Mali PTE 里 **memory-group tag（bits 59..62）** 的 SoC 侧消费者；
   在 MTK 上它落到 **SLC（System Level Cache）group**。
   `gpufreq_mt6983.c` 的上电序列末尾有单独一步 `__gpufreq_slc_control()`。
   **shim 只采样过 `0x13fbf748`（slc_group6），从未确认过 group 6 的策略真的被
   写过**——而 shim 的叶子恰好把 tag 设成 6。
2. **`arm,protected-memory-allocator` + GMPU**：DT
   `gmpu_table_size = 0x400000`、`protected_reserve_size = 0x1000000`、
   `reg-names = "gpueb_base"`。`protected_memory_allocator.c` 本身只是一个
   位图分配器（不写 GMPU），真正使能保护表的是 DDK 的
   `mali_kbase_csf_protected_memory.c`。**XNU 侧没有任何 GMPU 状态**，
   需要确认 LK 交付时 GMPU 是否已被打开。
3. **`L2_MMU_CONFIG`（0xF0C）**：`mali_kbase_l2_mmu_config.c` 的
   `kbase_set_mmu_quirks()` 会按 product model 写入 AID 限流字段
   （`KBASE_AID_32`），arch-10 走默认 `GENMASK(25,24)/GENMASK(27,26)`。
   2407 读回 `0xF0C = 0`；panthor 对 arch-10 也不写，**不是墙的候选**，
   但如果以后要压带宽，这里是厂商的入口。

## 7. OnePlus 仓库的作用

`OnePlusOSS/android_kernel_5.10_oneplus_mt6983` 是同一颗 MT6983 的高通/MTK
混合树中的 MTK 分支版本，其 GPU 侧与 `rubens-s-oss` 同源（同为
`mediatek/gpu_mali/mali_valhall/mali-r3xp*` + `gpufreq/v2` + `gpueb`）。
用它做的交叉验证只到"平台层结构相同"这一层：`gpufreq_power_control` 的
AOC/Buck/MTCMOS/Clock/PDCv2/SLC 顺序、GPUEB 的 IPI 电源接口、以及
`mali` 节点的 `physical-memory-group-manager` 绑定，三者一致。
**因此本项目的平台层不需要按 OnePlus 改写**；能借鉴的只有它对
`GPU_STATUS`/中断的清理习惯（第 4 节第 1 步）。

## 8. 墙：把已知的都说清楚

设备实测（本系列 2396–2407，21 个地址点，六种页编码，取指与数据两个方向）：

- MCU 访问的**物理地址 bit 9 = 1 → 事务永不完成**，无 fault、无
  `AS_FAULT`、`MCU_STATUS` 保持 1；
- 2406 把这条规则推进到**页表遍历本身**：一次 VA bit9=0 的访问，因为它的
  L3 descriptor 落在 PA bit9=1 上，整个 walk 挂死。**所以问题在页表之下、
  DRAM 之上，任何叶子/属性/VA 都改不动它。**
- 2407 排除了"某个 L2 切片被关掉"：`L2_PRESENT=1`、`0x048` 低半为零、
  `0x2c0..0x2cc` 全零。

**新增的、必须一起解释的两条异常（本文首次并列）**：
`GPU_STATUS.DBG_ENABLED` 常驻为 1，且 SOFT_RESET 不完成。
如果 GPU 处于 halt/调试态，那么它不对部分地址应答是**有可能**的；
这条线索此前被当作"复位只是收尾动作"忽略了。

## 9. 下一步（按性价比排序）

1. **复位先行（2408，本文已入库实现）**：按 panthor 的顺序，在碰 AS 之前
   `GPU_CMD=0x101`、清 `INT_CLEAR.bit8`、等 `RESET_COMPLETED`，并把
   `GPU_STATUS` 前后值留在既有报告字段里（不加 ABI）。若复位能完成且
   `DBG_ENABLED` 清零，则 2409 重飞 2406 的阶梯；若复位仍不完成，
   则"墙"要先在复位握手上解决，而不是内存。
2. **室外页（2409 候选，需要一个新原语）**：把 VA `0x0100D000` 映射到
   **arena 之外**的一页（framebuffer `0x9c000000` 最省事），读
   `0x0100D200`（VA/PA bit9=1，**不在 arena**）与 `0x0100D400`（bit9=0）。
   返回 → 死的是 arena 这块物理区间（换 arena 即可绕过）；
   挂死 → bit 9 是全局的，转向 SLC/MGM 与 GMPU。
3. **SLC/MGM**：读 `0x13fbf748` 一族确认 group 6 策略是否真的配过；
   未配则按 `__gpufreq_slc_control()` 补写，再飞。
