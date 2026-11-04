# MT6983 GPU 上电第二步：gpufreq DVFS 与共享状态观测

日期：2026-11-04。构建号 2338。本文只描述设计与证据边界，
不含已经上机的结果——2338 尚未在任何设备上运行。

## 为什么要补这一层

厂商 kbase 的 GPU 上电是**两步**，而 shim 从 2321 起只做了第一步：

| 步 | 厂商调用 | IPI 命令 | 本仓库状态 |
| --- | --- | --- | --- |
| 1 | `gpufreq_power_control(POWER_ON)` | `CMD_POWER_CONTROL` = 6 | ✅ 2321 起已实现 |
| 2 | `gpufreq_commit(target, oppidx)` | `CMD_COMMIT` = 7 | ❌ 2337 之前从未实现 |

来源（pinned 本地副本，gitignored）：
`research/matisse/20261031-gpu/platform-source/gpufreq_v2.c:853` 与 `:912`；
kbase 侧调用点见 `kbase-full-disasm.txt:2692` 的 `mtk_common_gpufreq_commit`。

`CMD_POWER_CONTROL` 在 GPUEB 内部依次做 AOC → Buck → MTCMOS → **Clock** →
MFG 寄存器恢复（`gpufreq_mt6983.c:740-800`）。所以第一步确实把时钟打开了，
但**频率与电压仍由 LK 遗留状态决定**，shim 既没有设置也没有测量过。

后果：2332–2336 全部在 MCU 启动处超时（`MCU_STATUS=1`、`GLB_VERSION=0`、
`JOB_RAW=0`），而这些试验**无法区分**两种解释：

- MCU 根本没取到指（页表/映射/入口问题）；
- 时钟频率或供电不在可执行范围（厂商自己的 `wait_ready()` 注释：
  `AS_ACTIVE bit stuck, might be caused by slow/unstable GPU clock or
  possible faulty FPGA connector`，`mali_kbase_csf_firmware-r32p1.c:305`）。

补齐第 2 步，并且把 GPUEB 发布的频率/电压读回来，才能把这两种解释分开。

## 协议

`CMD_INIT(0)` 把 0x400 字节 status 与 0xc00 字节 debug 交给 GPUEB
（`shim/gpu.c` 已实现）。之后 GPUEB 把 `struct gpufreq_shared_status`
写进那个 status 区。

报文沿用既有 32 字节布局（与 INIT/POWER 同格式）：

| 偏移 | CMD_COMMIT(7) | CMD_GET_FREQ_BY_IDX(1) |
| --- | --- | --- |
| 0 | LE32 cmd = 7 | LE32 cmd = 1 |
| 4 | LE32 target | LE32 target |
| 8 | LE32 oppidx (s32) | LE32 oppidx (s32) |
| 12..31 | 0 | 0 |

`target`：`TARGET_DEFAULT=0`、`TARGET_GPU=1`、`TARGET_STACK=2`
（`gpufreq_v2.h:78-81`）。应答的返回值/频率在 offset 8。

## 共享状态字段（只解码前 0x70 字节）

偏移取自 `gpufreq_ipi.h` 的 `struct gpufreq_shared_status`：

| 偏移 | 字段 | 用途 |
| --- | --- | --- |
| 0x00 | `cur_oppidx_gpu` | 当前 OPP，-1 表示未选 |
| 0x08 | `opp_num_gpu` | **解码判别位**：未写入的区域恒为 0 |
| 0x10 | `cur_fgpu` | kHz；0 表示"尚未发布" |
| 0x18 | `cur_vgpu` | uV；0 表示"尚未发布" |
| 0x20 | `cur_vsram_gpu` | uV |
| 0x60 | `power_control` | MFG 供电时厂商置 1 |
| 0x64 | `dvfs_state` | 厂商枚举，只记录不判据 |
| 0x68 | `shader_present` | 与 GPU 寄存器对照用 |
| 0x6c | `power_count` | GPUEB 认为持有的引用数 |

`mtk_gpufreq.h` 只解码这些字段；其余成员要么是 debug 专用，要么
没有在本机核实过，一律不解读。

## 证据边界

这一层最容易犯的错是把"读到 0"当成结论。所以设计成三条：

1. **不对称解释**。解码成功 = 有信息；解码失败（全 0、全 1、
   `opp_num_gpu` 越界）= **不可推断**，不是"没上电"。
   GPUEB 是否 flush 过 status 区未知，陈旧零值完全可能。
2. **纯观测不 gate**。基线与 POWER_ON 后两次采样只记录，
   不改变 `shim_gpu_prepare()` 的放行条件。只有我们**主动发出**的
   `CMD_COMMIT` 失败才 fail-closed。否则一次试验会浪费在假阴性上。
3. **用 IPI 应答交叉验证**。共享内存可能陈旧，IPI 应答不会。所以对
   `cur_oppidx_gpu` 发一次 `CMD_GET_FREQ_BY_IDX`：两者一致才置
   `gpufreq_valid` bit2，说明这块共享区是活的。

`gpufreq_valid` 各位：

| 位 | 含义 |
| --- | --- |
| bit0 | INIT 之后的基线样本可解码 |
| bit1 | POWER_ON + SPM 复核之后可解码（决定性样本） |
| bit2 | IPI 应答与共享内存的频率一致 |
| bit3 | 发出的 COMMIT 被第二次采样证实生效 |

## 报告 ABI

`sweet_gpu_boot_report` 从 72 字节扩到 **112 字节**，仍装得进
`shim/gpu.c` 里 128 字节的 `sweet-gpu-report` ADT 槽位，所以
**ADT 布局、`sweet-csf-report` 的 696 字节、以及 CSF 报告补丁链都不动**。

XNU 侧由 `xnu/patches/0136-matisse-gpu-dvfs-evidence.patch` 把
`sweet_gpu_report_marks()` 从 9 个 qword（mark 300..308）扩到 14 个
（mark 300..313），`SWEET_BUILD_ID` 由 `0137` 提到 `0x2338`。

## 2338 的构建约束

2338 **必须**保持 2337 的 CSF 探针配置（`--entry-probe --inline-entry
--entry-pte-guard`），镜像构建器会拒绝其他组合。这样 2338 相对 2337
只有一个变量：DVFS 层。

默认 `SWEET_GPU_DVFS_COMMIT=0`，即不发 COMMIT，只观测。
`--dvfs-commit current` 会提交"GPUEB 已经报告的索引"，走通完整命令路径
而**不改变频率**——这是端到端验证 `CMD_COMMIT` 最安全的形式。

## 2338 能证明什么

能证明：GPUEB 是否真的把 MFG 电源引用计数加上了；GPU 当前频率/电压是多少；
`CMD_COMMIT` 这条路径通不通。

不能证明：MCU 能启动、固件就绪、shader 可执行、Vulkan/Metal 可用。
`GLB_VERSION` 仍必须由 MCU 自己的 global-interface 中断来证。

## 2338 实测结果（2026-11-04）

一次被授权的 `boot_a` 试验，镜像 `ad07f492…34dcca`，
`--dvfs-commit current`。跑完后 `boot_a` 已完整恢复为 `2931647a…`，
设备回到 Recovery。

```
gpufreq.valid        15        四个观测位全部置位
gpufreq.oppidx       2
gpufreq.opp_num      5
gpufreq.power_count  1
gpufreq.freq_khz     610000    -> 610 MHz
gpufreq.power_ctrl   1         GPUEB 认为电源已开
gpufreq.dvfs_state   0         DVFS_FREE（不是 DISABLE/POWEROFF/KEEP）
gpufreq.commit_result 0        CMD_COMMIT 被接受
```

设备自己的 banner 独立印证：`q=f f=094ed0 pc=1`（0x94ED0 = 610,000）。

`volt_uv=65000` / `vsram_uv=75000` 的原始值与常见微伏量纲差十倍，
因此本报告**不使用**这两个值做任何判断，只记录原始读数。

### 这排除了什么

"时钟不可用"这条假设可以排除。GPU 在 610 MHz 上、DVFS 处于 FREE、
电源引用计数为 1、`CMD_COMMIT` 被接受。厂商 `wait_ready()` 注释里
暗示的"slow/unstable GPU clock"不成立。

### GPU / CSF 段与 2337 逐字段相同

`stage=8`、`error=-53`、`mcu_status=1`、`version=0`、`job_raw=0`、
`as_present=0xff`、`reset_raw=0x200`、`spm 3/7/3` —— 全部与 2337 一致。
DVFS 层的加入没有改变任何既有的放行条件，这符合设计意图。

### 失败点被收窄到 MCU 本身

三条独立证据指向"MCU 一条指令都没执行"：

1. `entry_marker_observed = false`。entry guard 把检查点放在固件入口
   （VA `0x010018ec`，shared+0xffc）；MCU 只要执行第一条指令就会写它。
   试验前后都是 0。
2. `job_raw = 0`，global-interface 的 bit31 从未出现。
3. `disable_status = 1`。cleanup 写 `MCU_CONTROL=0` 后轮询 `MCU_STATUS`
   直到 0 超时，状态**卡在 1 不动** —— MCU 对控制位没有响应。

另一方面 `MCU_STATUS=1` 表示 enable 位置起且 `HALTED`(bit1) 为 0。
即：寄存器层面"已启用、未停机"，硬件层面完全不执行。

### 下一步的假设

- `MCU_CONTROL` 写 2(AUTO) 是否应改为 3(ENABLE|AUTO)，或先 ENABLE 再 AUTO；
- MCU 是否有独立于 GPU 核心时钟/复位的门控，GPUEB 的
  `CMD_POWER_CONTROL` 只覆盖 MFG 域；
- 固件入口地址是否需要显式编程（当前依赖固件自身布局）。

这三条都能在离线用厂商源码与反汇编先筛，再决定要不要再花一次试验。
