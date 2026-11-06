# matisse / MT6983 厂商 GPU 驱动审计（Mali r32p1）

日期：2026-11-06 23:40。范围：`MiCode/Xiaomi_Kernel_OpenSource` 分支
`rubens-s-oss` 中的 `drivers/gpu/mediatek/gpu_mali/mali_valhall/mali-r32p1`，
以及树外的 `gpufreq_mt6983.c`。本文只做静态对照，没有改设备。

下文用 `V/` 代表
`…/mali-r32p1/drivers/gpu/arm/midgard`，用 `S/` 代表本仓库的 `xnu/gpu/`。

---

## 0. 一句话结论

厂商驱动里**没有任何 reset 入口地址 / 512 字节对齐的约束**；启动只有一个
`MCU_CONTROL = 2` 的写，然后等 `JOB_IRQ.bit31`。所以 2391 看到的 512 规则
不是“少抄了厂商某一步”。

但审计同时发现：**2391 镜像的页属性并不是厂商等价物**。
当前构建用 AttrIdx 1 / MEMATTR `0x4c4c9f4c` / 叶子带 nG / 代码页可写；
厂商在同样的 non-coherent SoC 上用 AttrIdx 0 / MEMATTR `0x888d8f88` /
叶子不带 nG / 代码页只读。2380 开过一次厂商配对并回读到 `memattr_lo=0x888D8F88`，
但 2380 没有 cold-boot 探针，之后 2381–2391 又全部回到 shim 默认。
这是目前唯一还没排除的 shim 侧变量。

---

## 1. 厂商驱动地图

| 模块 | 文件 | 职责 |
|---|---|---|
| 设备/探测 | `V/device/backend/mali_kbase_device_csf.c` | probe、寄存器映射、把固件加载延迟到第一次 `open()` |
| 固件 | `V/csf/mali_kbase_csf_firmware.c` | 解析容器、映射 section、装 AS、发 `MCU_CONTROL`、`global_init` |
| CSF 核心 | `V/csf/mali_kbase_csf.c` | 全局接口中断、门铃、CSG/CS 队列 |
| 调度 | `V/csf/mali_kbase_csf_scheduler.c` | CSG 调度、挂起/恢复 |
| MMU | `V/mmu/backend/mali_kbase_mmu_csf.c`、`V/mmu/mali_kbase_mmu_hw_direct.c`、`V/mmu/mali_kbase_mmu_mode_aarch64.c` | AS 寄存器、页表、叶子编码 |
| 电源/复位 | `V/backend/gpu/mali_kbase_pm_driver.c` | 软复位、L2、IRQ mask、CSF_CONFIG 恢复 |
| 平台钩子 | `V/platform/mt6983/mali_kbase_config_mt6983.c` | `gpufreq_power_control(POWER_ON/OFF)` |
| 平台电源 | 树外 `gpufreq_mt6983.c` | MTCMOS、Buck、clock/PLL、SLC、DVFS |

关键点：Mali 树内**没有** MTK GPUEB 代码。`grep -i gpueb` 零命中；
GPUEB 协议在树外的 `gpufreq` / GPUEB 固件侧。shim 自己实现了 IPI，
这部分无法用 Mali 驱动对照。

---

## 2. 厂商启动链路（按执行顺序）

1. 平台 `gpufreq_power_control(POWER_ON)`：AOC → Buck → MTCMOS → clock/PLL →
   MFG 寄存器恢复 → PDC → ACP → HWDCM → **SLC policy**（`gpufreq_mt6983.c:760-820`）。
2. `kbase_pm_disable_interrupts()`：GPU/JOB/MMU 三组 mask 清零、clear 全 1
   （`V/backend/gpu/mali_kbase_pm_driver.c:2047-2063`）。
3. `GPU_COMMAND = 0x101`（soft reset），只开 `RESET_COMPLETED`，等它
   （`:2548-2583`）。
4. `kbase_pm_hw_issues_apply()`：写回 `SHADER_CONFIG`、`TILER_CONFIG`、
   `L2_MMU_CONFIG`、`CSF_CONFIG`（`:2487-2503`）。这些值是 probe 时读回的
   硬件默认值（`:2336-2337`），没有 DT quirk 时等于原值。
5. `COHERENCY_ENABLE(0x304) = system_coherency`。本机 DT 没有
   `system-coherency`，`kbase_core_linux.c:4891` 默认 `COHERENCY_NONE(31)`。
6. `kbase_pm_enable_interrupts()`：GPU `0x80503`、JOB `0xFFFFFFFF`
   （含 bit31 `JOB_IRQ_GLOBAL_IF`）、MMU `0xFFFF`
   （`V/backend/gpu/mali_kbase_pm_driver.c:2019-2043`）。
7. L2 上电：等 `L2_PWRTRANS` 清 → 写 `L2_PWRON = L2_PRESENT` → 等
   `L2_READY`（`:855-960`）。
8. 解析固件头：magic `0xC3F13A6E`、major 0、`entry_end_offset`
   （`V/csf/mali_kbase_csf_firmware.c:1746-1798`）。
9. 逐条目解析；每个 memory-setup 条目分配 4 KB 页、按 `data_start/end`
   拷贝、按 `ZERO` 标志清零、逐页 `DMA_TO_DEVICE`，再
   `kbase_mmu_insert_pages_no_flush()`（`:377-412`、`:473-665`）。
10. 记录 VA `0x04000000` 的段为 shared interface（`:627-632`）。
11. `kbase_pm_wait_for_l2_powered()`（`:1818-1819`）。
12. 装 AS：`AS_TRANSCFG` → `TRANSTAB` → `MEMATTR` → `AS_COMMAND=UPDATE`
    （`V/mmu/mali_kbase_mmu_hw_direct.c:149-169`）。
    本机值：`TRANSCFG=0x42000006`、`MEMATTR=0x00084C8D888D8F88`、
    `TRANSTAB=pgd`。
13. **`MCU_CONTROL(0x700) = 2`（AUTO）**，只此一个写
    （`V/csf/mali_kbase_csf_firmware.h:473-480`）。`MCU_CNTRL_ENABLE(1)`
    在整棵树里从未被写。
14. 等 `JOB_IRQ_STATUS.bit31`，超时 500 ms；超时只 `dev_err`，不返回失败
    （`V/csf/mali_kbase_csf_firmware.c:238-261`）。
15. `parse_capabilities()` 读 `GLB_VERSION`；为 0 判固件没起来
    （`:944-1034`）。
16. `global_init_on_boot()`：写共享页的 `GLB_INPUT`（`PROTM_COHERENCY`、
    `ALLOC_EN`、`PWROFF_TIMER`、`PROGRESS_TIMER`、`ACK_IRQ_MASK=0x0480031E`），
    再 ring doorbell 0，等 `GLB_ACK`，超时 3000 ms（`:1374-1435`）。
17. `kbase_csf_firmware_cfg_init()` 建 sysfs；之后才把 `mcu_state` 设为 ON
    （`V/device/backend/mali_kbase_device_csf.c:430-437`）。

---

## 3. 与 shim 的逐项对照

| 项目 | 厂商 | shim（2391 实际） | 结论 |
|---|---|---|---|
| 固件头/条目解析 | magic、major、entry table | 相同 | 一致 |
| section 拷贝/清零 | 逐页拷贝 + ZERO 清零 | 整 arena 清零后拷贝 | 等价 |
| protected section | 无 PMA 时跳过 | 跳过 | 一致 |
| shared VA | 必须 `0x04000000` | 强制 `0x04000000` | 一致 |
| TRANSCFG | `0x42000006`（NONE） | `0x42000006` | 一致 |
| TRANSTAB/UPDATE | 写 root + UPDATE | 相同，另加 LOCK/FLUSH | 等价或更严格 |
| MEMATTR | `0x888D8F88/0x00084C8D` | 默认 `0x4C4C9F4C/0x4C4C4C4C` | **不一致** |
| 叶子 AttrIdx | cached→0，其它→5 | 默认 cached→1，其它→0 | **不一致** |
| 叶子 SH | 仅 `SHARE_BOTH`；本机 shared 降级为 NONE，无 SH | shared 段 `SH=3` | **不一致** |
| 叶子 nG（bit11） | 从不置 | **恒置 `0x800`** | **不一致** |
| 叶子 AP | RW/RO 按 flags | `--ro-as-rw` 让只读段也可写 | **不一致** |
| L2 上电 | 等 PWRTRANS→PWRON→READY | 相同 | 一致 |
| 一致性 | DT 无属性 → NONE(31) | 写 31 并回读 | 一致 |
| GPU IRQ mask | `0x80503` | `0x80503` | 一致 |
| JOB IRQ mask | `0xFFFFFFFF`（含 bit31） | `0xFFFFFFFF` | 一致 |
| MMU IRQ mask | `0xFFFF` | `0xFFFF` | 一致 |
| `MCU_CONTROL` | `2`（AUTO） | `2`（AUTO） | 一致 |
| 启动等待 | JOB bit31，500 ms | JOB bit31 轮询，1000 ms | 等价 |
| `GLB_VERSION` 判据 | 0 → 失败 | 0 → 接口门失败 | 一致 |
| `global_init` | 启动后立即做 | 默认关闭（`SWEET_CSF_GLOBAL_INIT=0`） | **缺失**（post-boot） |
| `CSF_CONFIG`/SHADER/TILER/L2_MMU 恢复 | 软复位后写回默认值 | 不写 | 可能无副作用，未验证 |
| SLC policy | 每次 POWER_ON 写 group0–9 | 不写；只读 group6 | 实测 `0x06002006`，当前正确 |
| clock/PLL | `clk_mux`/`clk_sc_mux` 切主 PLL | 交给 GPUEB IPI | 实测 `power_count=1`、610 MHz |
| protected 模式 | 有 PMA 才支持 | 不支持 | 一致（本机无 PMA） |
| CSG/queue/scheduler | 完整 | 无 | 超出台阶，功能缺失 |

### 3.1 叶子编码的具体差值

2391 的代码页叶子（读回）：`0x30000000401A4C47`，低 32 位 `0xC47`：

```
0xC47 = 0x800 (nG) | 0x400 (AF) | 0x40 (AP[1]) | 0x4 (AttrIdx 1) | 0x3
```

厂商同页、同 flags（R-X、CACHED、group 6）应写：

```
0x4C3 = 0x400 (AF) | 0xC0 (RO: AP[2]=1,AP[1]=1) | 0x0 (AttrIdx 0) | 0x3
```

差值 = `0x800 + 0x4 - 0x80 = 0x784`（shim 多 nG、多 AttrIdx 1，少 AP[2]）。
数据段同理（厂商 `0x443`，shim `0xC47`）；shared 段厂商 `0x457`（AttrIdx 5），
shim `0xF43`（AttrIdx 0 + SH=3 + nG）。

---

## 4. 真正的缺口（按影响排序）

### G1. 页属性不是厂商等价物（最高优先）

- 2391 manifest：`csf_vendor_memattr=false`、`csf_readonly_leaves_writable=true`。
- 2380 开过一次厂商配对（MEMATTR + AttrIdx），报告回读 `memattr_lo=0x888D8F88`；
  但 2380 没有 cold-boot 探针，之后 2381–2391 又全部回到 shim 默认。
- 因此 2391 的 512 规则是在 **AttrIdx 1 / MEMATTR[1]=0x9F / nG=1 / 代码可写**
  这套属性下观察到的，不能直接当成硬件性质。
- 这是目前唯一还能由 shim 侧改变、且可能影响取指的变量。

### G2. 没有 `global_init`

厂商在 `MCU_CONTROL` 之后立刻写共享页并 ring doorbell；shim 默认完全不做。
这不会阻止第一次取指，但会让“固件跑起来”之后无法进入可用状态。等 G1 解决、
`GLB_VERSION` 非 0 之后，必须补上。

### G3. `CSF_CONFIG` / `SHADER_CONFIG` / `TILER_CONFIG` / `L2_MMU_CONFIG` 未恢复

厂商在软复位后把 probe 读到的默认值写回；shim 不写。没有 DT quirk 时这些值
等于复位默认，预计无副作用，但应在下一次 trial 里读回确认，而不是假设。

### G4. SLC / clock 不由 shim 拥有

厂商每次 `POWER_ON` 都重写 SLC group0–9 和 clock/PLL；shim 依赖 LK/GPUEB 的遗留值。
2391 实测 `slc_group6=0x06002006`（与厂商 group6 控制字一致），
`rpc/infra/emi` 均未 blocked，`freq=610 MHz`。**当前不是缺口，但很脆**：
一次 GPU 电源域循环就可能把 SLC 策略清掉，而 shim 不会恢复。

### G5. 启动成功判据不可观测

shim 的报告门要求 `version != 0`，但 `version` 只在固件写 `GLB_VERSION` 后才非 0；
一旦固件没起来，报告只剩 `stage 4 / error -53 / cleanup_error -53`。
厂商也是用 `GLB_VERSION==0` 判失败，但 shim 没有 JOB bit31 这一层的独立证据。
建议把 `JOB_IRQ_STATUS.bit31`（启动完成中断）单独记进报告。

### G6. protected section 不映射

与厂商在“无 PMA”时一致。若后续要跑 protected mode，需要补 PMA；当前不是墙。

### G7. 没有 CSG/queue/scheduler

这是“能启动”与“能跑图形”的差距，不是当前取指墙的一部分。等 G1/G2 解决后再做。

---

## 5. 对 512 规则的含义

厂商代码里：

- 没有 `MCU_PC` / `MCU_BOOTADDR` / `RESET_VECTOR` 寄存器；
- 没有 512、`0x200`、`0x1FF` 与 entry/boot/fetch 相关的常量或注释；
- 唯一的对齐检查是 memory-setup 条目的 `virtual_start/end` 必须 4 KB 对齐
  （`V/csf/mali_kbase_csf_firmware.c:508-513`）；
- VA 0x0 的 SP/reset 向量完全由固件与 MCU 硬件约定，驱动不读、不写、不校验。

**所以 512 规则不是“厂商驱动里少写了一步”。** 它只可能来自两层：

1. MCU 硬件/固件对 reset 入口地址的解释（例如 512 对齐但非 4 KB 页基被当成
   某种描述符指针）——这是目前最像的解释，但需要硬件文档或更多实验；
2. shim 的非厂商页属性让取指在特定地址上表现异常。

现有 2391 证据无法分开这两层，因为所有 512 测试都跑在非厂商属性下。
在 G1 修掉之前，把 512 规则写成“硬件规则”是过度推断；文档里应降级为
“当前属性编码下的观测规则”。

---

## 6. 下一步：三次 trial 的判别矩阵

| build | 页属性 | 向量 | 回答的问题 |
|---|---|---|---|
| 2392 | 当前（AttrIdx 1/0、nG、代码可写） | `0x0100EA01` | 现有属性下，512 规则是否仍在？ |
| 2393 | 厂商（AttrIdx 0/5、无 nG、代码只读） | `0x0100EA01` | 换成厂商属性后，512 目标是否能跑？ |
| 2394 | 厂商 | `0x01001A01` | 若 2393 能跑，`0x1A00` 本身是否仍然特殊？ |

推荐顺序：**2392 → 2393**。
- 2392 跑通 → 512 规则被推翻，转向 C（沿 `0x18EC` 布点）。
- 2392 不跑、2393 跑 → 墙是页属性，不是地址；这是最好的结果，直接改默认编码。
- 2392/2393 都不跑 → 512 规则在厂商属性下仍成立，基本可判为硬件/固件行为，
  再跑 2394 确认 `0x1A00`，然后转 C。

### 实现 2393 需要的改动

1. `tools/matisse-shim-gpu-image.py`：允许 2392+ 使用 `--vendor-memattr`，
   并新增 `--vendor-leaves`；`--ro-as-rw` 对 2393 关闭。
2. `xnu/gpu/mali_csf_memory.c`：在 `SWEET_CSF_VENDOR_LEAVES=1` 时不要写
   `0x800`（nG）；AttrIdx/SH 已由 `SWEET_CSF_VENDOR_MEMATTR` 处理。
3. `xnu/gpu/mali_csf_boot.c`：`SWEET_CSF_VENDOR_LEAVES=1` 时 `memattr` 必须用
   厂商表，不能落回默认 `0x4c4c9f4c`。
4. manifest 增加 `csf_vendor_leaves`，报告解码器记录该字段。
5. 测试：断言代码页叶子 = `0x4C3`（低 32 位），shared 页 = `0x457`。

---

## 7. 需要修正的现有文档

1. `docs/matisse-gpu-csf-status.md` 第 3 节事实 2 说 “AS_MEMATTR 与厂商一致”，
   这只对 2380（开了 `--vendor-memattr`）成立；2381–2391 实际用的是
   shim 默认表。应改成“2380 验证过厂商值；当前镜像未使用”。
2. 同一文档第 9 节把 512 规则写成结论；应降级为“当前属性编码下的观测”，
   并指向本文第 5 节。
3. `NOTES.md` 的 ACTIVE 横幅应加一行：vendor 审计发现页属性未对齐厂商，
   下一次 trial 先补这个变量。

---

## 8. 参考位置

- 厂商固件解析：`V/csf/mali_kbase_csf_firmware.c:75-77, 315-412, 473-665, 1746-1798`
- 厂商 AS：`V/mmu/backend/mali_kbase_mmu_csf.c:37-61`、
  `V/mmu/mali_kbase_mmu_hw_direct.c:149-169`
- 厂商叶子：`V/mmu/mali_kbase_mmu_mode_aarch64.c:110-152`
- 厂商 MCU：`V/csf/mali_kbase_csf_firmware.h:473-480`、
  `V/csf/mali_kbase_csf_firmware.c:238-261`
- 厂商 IRQ：`V/backend/gpu/mali_kbase_pm_driver.c:2019-2043`
- 厂商 global init：`V/csf/mali_kbase_csf_firmware.c:1374-1435`
- 厂商 SLC/clock：`gpufreq_mt6983.c:760-820, 3197-3300, 3762-3790`
- shim AS：`xnu/gpu/mali_csf_boot.c:330-352`
- shim 叶子：`xnu/gpu/mali_csf_memory.c:157-176`
- shim MCU：`xnu/gpu/mali_csf_boot.c:399-416`、`shim/csf.c:47-56`
