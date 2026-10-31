# Redmi K50 Pro：XNU 实机进展与 iOS 启动路线

更新：2026-10-23，完成调度器启动、定时 IRQ、lockdown、单 CPU kperf 修复，并在实机执行 `bsd_init`、成功挂载 mockfs/md0 根、到达 `load_init_program`。PID 1 持续运行仍未证实，生产启动屏幕仍黑。

**当前结论：这台 K50 Pro 已执行真正的 XNU，完成早期 MMU、正式页表、平台与 CPU/GIC 初始化，并进入 `kernel_bootstrap`；`vm_mem_bootstrap` 已完整返回，包括 `vm_page_bootstrap`、`zone_bootstrap`、`vm_object_bootstrap`、`vm_map_init`、`kmem_init`（含 KMEM/ZALLOC 启动阶段和 `zone_init`）与 `vm_fault_init`。`sched_init`、task/thread 初始化与 `load_context` 也已实机运行。此后 `idle_thread_create`、`sched_startup`（含首次真正的 `thread_block` 往返）、`thread_daemon_init`、`spllo`、`initialize_screen`、`machine_lockdown`、`PE_lockdown_iokit`、`vm_set_restrictions`、完整 CONFIG_XNUPOST 测试套件与 `kperf_init_early` 均已实机返回；执行已到达 `kernel_bootstrap_thread` 末尾的 `bl bsd_init` 调用点。500 ms CNTVCT 等待期间 `sched_tick` 增加 3，证明定时中断和调度维护线程在正常 XNU 向量下持续运行。后续 RAM-disk 探针已证明 `bsd_init` 执行、`vfs_mountroot` 以 `x0=0` 成功返回、mockfs/md0 根已挂载，并运行到 `bsd_utaskbootstrap` 与 `load_init_program`。PID 1 是否持续运行仍未证实；尚未启动 iOS 的 `launchd` 或桌面。生产屏幕黑的问题已定位到显示驱动漏掉图形控制台刷新，并把瞬时 `TE_RDY` 状态误作初始化门槛；修复补丁正在验证，尚无真机显示结果。**

本轮经历两次无限重启和多轮自动返回：`bsd_init` 大跳与 XNUPOST-skip 诊断都未返回，均由用户手动进入 fastboot、写 20,873,216 字节 trimmed 原厂前缀、进 Recovery 后写回完整 64 MiB 并校验；定位到根因是单 CPU 拓扑下 `kperf_init_early()` 的 `ml_wait_max_cpus()` 永久等待，而 matisse 的 `arm,cortex-a510` CPU 节点不匹配只声明 `qcom,kryo470` 的 SweetCPU 驱动。临时 payload 跳过 kperf 后到达 `bl bsd_init`；随后用 `ml_wait_max_cpus()` 单 CPU 早返回的正式补丁经 CI 重建内核，并在实机端到端验证通过。完整 67,108,864 字节 `boot_a` 已恢复并校验。本轮没有写入 `userdata`。详细逐次记录以 [NOTES.md](../NOTES.md) 顶部 ACTIVE 区为准，下面历史记录可能代表已经被后续证据替代的判断。

## 1. 项目是什么，哪些成果可以复用

本项目将 Apple 开源 XNU 8796 系列移植到非 Apple ARM64 手机，再提供 iOS 用户空间需要的文件系统、系统调用、IOKit 服务和设备驱动。它运行独立内核，不依赖 Android 内核承载 iOS 进程。

需要严格区分两个目标设备：

| 项目 | 原目标 sweet | 当前在线设备 matisse |
| --- | --- | --- |
| 手机 | Redmi Note 10 Pro | Redmi K50 Pro |
| SoC | Qualcomm SM7150 | MediaTek MT6983 / Dimensity 9000 |
| 既有记录 | README、历史 NOTES 记录了 iOS 桌面和触摸成果 | 本次实测到调度器、定时 IRQ、lockdown 与 `bl bsd_init` 调用点 |
| 临时启动 | 原设备支持 `fastboot boot` | 本 LK 没有可用的 `fastboot boot` |
| 显示 | 1080×2400，连续扫描路径 | 1440×3200，DSC 命令模式，需要主动刷新 |
| 触摸 | Goodix，经 Qualcomm GENI I²C | ST FTS 路线，经 MTK SPI6，见第 6 节 |
| USB | Qualcomm 包装层内的 DWC3 | MediaTek MTU3 / SSUSB，另有 xHCI 主机路径 |

原机型的用户态兼容层、HFS+、Mach-O 加载、IOSurface、IOMobileFramebuffer 和 HID 接口值得复用；硬件寄存器、时钟、电源、DMA 和中断实现必须按 matisse 重做或验证。原机型的桌面成功记录不等于当前设备的桌面成功。

主要代码入口：

| 路径 | 作用 |
| --- | --- |
| `shim/board.c`、`shim/fdt.c` | 从 live FDT 获取板级资源 |
| `shim/loader.c`、`tools/mkpayload.py` | 装载 XNU Mach-O、生成 boot_args、放置 ADT 和可选 RAM disk |
| `tools/mkadt.py` | 构造 XNU 使用的 Apple Device Tree；提供 matisse 配置 |
| `tools/mkentryprobe.py` | 同次启动诊断包装器、断点与异常回传 |
| `tools/xnu_tickprobe.py` | 定时 IRQ/`sched_tick` 证明探针 |
| `xnu/patches/` | 内核、文件系统、平台服务和驱动补丁 |
| `.github/workflows/xnu.yml` | GitHub Actions 内核构建 |
| `tools/sweet-init.S`、`tools/mkinit.py` | 最小静态 ARM64 用户态 PID 1 |
| `tools/mkiosroot.sh`、`tools/sweet-root-tweaks.py` | 构建并调整 iOS 用户空间根镜像 |

## 2. 已经完成的全过程

### 2.1 从“只见 Redmi 标志”变成可定位的启动链

1. **确认硬件和恢复方式。** 识别实际设备为 matisse，保存启动分区等备份。LK 接受下载和刷写，但临时 `fastboot boot` 不可用，因此每次测试临时替换 `boot_a`，随后恢复。Recovery ramdisk 位于 `vendor_boot`，但启动仍依赖可工作的内核；不能认为坏的 `boot_a` 一定能直接进 Recovery。
2. **验证 LK 确实跳入自定义代码。** 复位 stub 和入口探针建立了这一点。随后用同次启动探针确认真实入口为 EL1、13 MHz 计时器、GICv3；不能根据 LK 的 `via EL2` 字样判断实际异常级别。
3. **修正板级资源与镜像布局。** 适配 boot header v4、live FDT、四单元 GIC timer 描述、正确 framebuffer、上部 RAM 和嵌入内核 Image 的 payload。修复只扫描对齐地址等问题。旧完整 shim 仍有未解释的失败，不能把这些修复直接等同于完整 shim 已成功。
4. **打通显示对照。** 由于面板是命令模式，只改显存不会自动更新。受控刷新测试中，用户看到了 `DISPLAY KICK` 与移动绿条，也看到了 EL1 测试文字。这证明在当前 LK 遗留状态下可以刷新面板。
5. **建立同次启动证据。** 自定义代码运行后，把阶段或异常写入所携带的原 Linux banner，再转入 Recovery，从 `dmesg` 读取 `SWEET-ENTRY`。这避免依赖未经证明能跨重启保留的 DRAM 日志。
6. **确认加载路径。** 只加载、不跳 XNU 的镜像成功完成段复制、ADT 和 boot_args 准备并返回。完整 shim 与无断点直接跳转曾只显示 logo，部分需要手动 fastboot 恢复；logo 本身不说明停在哪。
7. **逐步推进真实 XNU。** 在实际内核指令流插入受控 BRK，从入口一路推进至当前的 `bl bsd_init` 调用点。每轮真机测试后恢复并验证整个分区。

### 2.2 XNU 断点证据

以下均为真机命中预期位置、自动返回 Recovery、随后完整恢复的结果。`ESR=0xf2005357` 是主动插入的 `BRK #0x5357`；它不是此次发现的真实内核崩溃。PC 的低地址为物理执行地址，高地址为 XNU 虚拟执行地址。

| 检查点 | 镜像 SHA256 前缀 | 记录 PC | 已证明的执行范围 |
| --- | --- | --- | --- |
| XNU 入口 | `386420a8` | `10148c488` | 已真正跳入 XNU |
| 首次切异常向量之前 | `1291e310` | `10148e104` | 原始入口分支及初始汇编 |
| bootstrap 页表完成 | `276ffdd7` | `10148e444` | 早期页表构建 |
| MMU 配置完成 | `36228bdb` | `10148e4f8` | TCR、TTBR、MAIR 等配置 |
| MMU 开启后 | `7937d19c` | `10148e530` | 真实 MMU 开启和启动环境设置 |
| 早期 C 代码 | `98e8829d` | `fffffe0007ad58b0` | `arm_init` 及早期控制台标记 |
| `arm_vm_init` 调用前 | `25d5d260` | `fffffe0007ad6124` | VM 初始化前的平台准备 |
| 正式页表构建完成 | `340b9628` | `fffffe0007483dd8` | 构造正式页表 |
| 正式 TTBR1 切换后 | `e9fbcb81` | `fffffe0007483ddc` | 正式内核地址空间可执行 |
| TTBR0 清空后 | `c73eb57f` | `fffffe0007483e18` | 旧低地址映射清理、TLB 刷新、重定位后日志调用 |
| `arm_vm_init` 返回 | `9ac98004` | `fffffe0007ad6128` | 完整 ARM VM 初始化 |
| `serial_init` 返回 | `e9888fe6` | `fffffe0007ad6164` | 返回值 `x0=1`，控制台初始化成功 |
| 后续平台初始化 | `a89bd1c0` | `fffffe0007ad62d8` | `PE_init_platform(TRUE)` 等返回 |
| `machine_startup` 调用前 | `34efc91a` | `fffffe0007ad63a0` | CPU、计时器、GIC 上下文和 early_random 初始化 |
| `vm_page_bootstrap` 返回 | `e9b81b88` | `fffffe0007abfab0` | 已进入 `kernel_bootstrap` → `vm_mem_bootstrap`，完成物理页管理初始化 |
| `zone_bootstrap`、`vm_object_bootstrap` 返回 | `e4231b90` | `fffffe0007abfad0` | 在 `vm_mem_bootstrap` 内连续完成 zone 与 VM object 初始化 |
| 完整 `vm_mem_bootstrap` 返回 | `99d68ed6` | `fffffe00073644d8` | `vm_map_init`、`kmem_init`、KMEM/ZALLOC 启动阶段、`vm_fault_init` 全部返回，`kernel_bootstrap` 继续执行 |
| 双槽选择性向量验证 | `81652ccf` | `fffffe00073644d8` | 只拦截 EL1t/EL1h 同步槽的 `BRK #0x5357`，诊断回传与完整恢复通过 |
| bootstrap thread 执行 | `154449c1` | `fffffe0007aaf74c` | `kernel_thread_create`、`load_context` 后，`kernel_bootstrap_thread` 运行到 `current_processor` 返回 |
| `sched_startup` 返回 | `c1859ef9` | `fffffe0007aaf7d4` | `idle_thread_create` 与首次真正 `thread_block` 往返（`sched_init_thread` 阻塞、bootstrap 恢复） |
| `thread_daemon_init` 返回 | `f16c296d` | `fffffe0007aaf80c` | 线程生命周期与 daemon 初始化 |
| `spllo`、`initialize_screen` 返回 | `ff8e21bf` | `fffffe0007aaf9ec` | 中断开启、`initialize_screen`、`PE_init_iokit` 等返回 |
| 定时 IRQ 与维护线程 | `80c8f80f` | `fffffe000748d744` | 500 ms CNTVCT 等待内 `sched_tick` 增加 3（x0=3），正常 IRQ 路径与调度维护线程持续运行 |
| `machine_lockdown` 返回 | `f68a28a8` | `fffffe0007aafb54` | `OSKextRemoveKextBootstrap` 与 lockdown 后，选择性向量、缓存清理和 bootstrap TTBR0 回传仍有效 |
| 正式 CI 内核 0084 + `bsd_init` 调用点 | `1cd72d23` | `fffffe0007aafc00` | 全新 CI 内核（补丁 0084），XNUPOST 与 kperf 未跳过，执行到达 `bl bsd_init` |

同轮诊断与失败记录：

| 检查点 | 镜像 SHA256 前缀 | 结果 |
| --- | --- | --- |
| `bsd_init` 大跳 | `7a5b60b5` | 未返回，无限重启；用户手动 fastboot 恢复 |
| XNUPOST-skip | `ce02efbf` | 仍未返回；排除 XNUPOST 为唯一根因 |
| NOP-kperf | `14bef24d` | 返回，`pc=fffffe0007aafbe0`；锁定 kperf 为阻塞点 |
| payload max_cpus 修复 | `8783158b` | 返回，`pc=fffffe0007aafbe0`；证明单 CPU 早返回即可通过 kperf 与 XNUPOST |
| 正式 CI 内核 0084 | `1cd72d23` | 返回，`pc=fffffe0007aafc00`；永久补丁端到端验证通过 |

`serial_init=1` 只证明函数返回成功；后期各轮没有收集用户的屏幕观察，不能宣称已经看到了 XNU 控制台。定时中断现在已有实机证据：`sched_tick` 在 500 ms 等待中增加 3，且这些 tick 发生在 XNU 自己的 IRQ 槽上。

### 2.3 为推进断点补齐的诊断能力

- MMU 关闭时的向量转发，以及 MMU 开启后的高地址异常回传。
- 恢复初始 `SPSel`、栈、SCTLR 和 Linux DTB 参数。
- 在返回 Linux 前显式清理 XNU 写过的缓存区域；最近一轮范围为物理地址 `[0x100000000, 0x108000000)`，共 128 MiB。
- XNU 清空 TTBR0 后，仅在异常回传时恢复 bootstrap TTBR0，保持原始初始化流程照常执行。
- 单独记录 x0，以区别函数“返回了”和“返回成功”。
- **选择性诊断向量（已实机验证）**：XNU 以 SPSel=0（EL1t）执行，内核 BRK 走同步槽 slot 0，而不是 slot 4；因此 stub 同时安装在 slot 0 和 slot 4。stub 检查 `ESR_EL1` 是否为 `BRK #0x5357`，是则进入诊断回传，否则通过安装时打补丁的直接 `B` 转交该槽的原始 XNU 处理器。转发路径保存并恢复 x16/x17，不改变任何通用寄存器；诊断 relay 复制到 arm64 用户态不使用的 AArch32 slot 12/13。IRQ、FIQ、SError 和 EL0 同步槽全部保持 XNU 原样，正常中断、SVC 和缺页异常不再被探针占用。
- **定时 tick 探针（已实机验证）**：`tools/xnu_tickprobe.py` 在 `initialize_screen` 返回点把原 `bl vm_commpage_init` 改为跳到早期向量表槽 14 的 cave；cave 保留原调用，读取 `sched_tick`，用 `CNTVCT_EL0` 忙等 6,500,000 tick（本机 13 MHz 下 500 ms），再读一次并相减，最后执行 `BRK #0x5357`。实机返回 `x0=3`，说明等待期间定时 IRQ 正常投递，且调度维护 continuation 至少运行了三次。

主机验证包括本轮运行的 44 项工具测试、选择性 stub 微测试和交叉编译。双槽修复后，vm-return、bootstrap-thread、sched/thread、spllo、lockdown 与正式内核检查点均在实机通过。选择性向量的 IRQ 转发现在有真实证据（`sched_tick` +3）；EL0 的 SVC/缺页尚未在完整引导中触发，但这两个槽保持 XNU 原处理器，未被探针占用。仓库全量检查此前还有六个已有 CRLF shell 问题，不能声称全仓检查已通过。

### 2.4 调度器、定时 IRQ、lockdown 与 `bsd_init` 前路径

- **调度器上下文切换通过。** `idle_thread_create` 与 `sched_startup` 返回，`pc=fffffe0007aaf7d4`。`sched_startup` 内的 `thread_block()` 切换到 `sched_init_thread` 后能切回 bootstrap thread，说明 task/thread、run queue 与 `machine_switch_context` 已完成首次真实往返。
- **线程生命周期初始化通过。** `thread_daemon_init` 返回，`pc=fffffe0007aaf80c`。
- **中断开启与屏幕初始化通过。** `spllo()` 使能 IRQ，`initialize_screen(NULL, kPEAcquireScreen)` 返回，`pc=fffffe0007aaf9ec`；同一段还包含 `PE_init_iokit` 与启动阶段 16。
- **定时 IRQ 与调度维护通过。** tick cave 在 500 ms 等待中读到 `sched_tick` 增量 3，`pc=fffffe000748d744`。这是“正常 XNU 向量下的持续 IRQ 投递”的直接证据，而不是只依赖函数返回。
- **lockdown 后诊断回传仍有效。** `OSKextRemoveKextBootstrap` 与 `machine_lockdown` 返回，`pc=fffffe0007aafb54`。`bootstrap_pagetables` 位于 `__DATA_CONST`（PA `0x10117c000`）；lockdown 释放的 `__BOOTDATA` 在 PA `0x102080000`，没有回收 TTBR0 恢复页。向量 stub 位于 `__TEXT_EXEC`，ROX 后仍可执行。
- **锁定阻塞点：单 CPU 的 `ml_wait_max_cpus()`。** 未修改内核的 `bsd_init` 大跳（`7a5b60b5`）与 XNUPOST-skip（`ce02efbf`）都进入无限重启；`machine_lockdown` 检查点（`f68a28a8`）正常返回，排除 lockdown/relay。NOP-kperf 诊断（`14bef24d`）返回 `pc=fffffe0007aafbe0`，锁定 `kperf_init_early()`。根因是它调用 `ml_wait_max_cpus()`，等待 IOKit CPU 驱动设置 `max_cpus_initialized`；matisse ADT 的 CPU 节点是 `arm,cortex-a510`，而 SweetCPU 只匹配 `qcom,kryo470`，驱动从未实例化。
- **单 CPU 早返回修复通过。** 临时 payload 把 `ml_wait_max_cpus()` 改成 `mov w0,#1; ret` 后，XNUPOST 与 kperf 都保持启用并到达 `bl bsd_init`（`8783158b`）。正式补丁 `0084-sweet-single-cpu-max-cpus.patch` 在 `machine_info.max_cpus <= 1` 时直接返回；CI `39828405447` 重建内核 `28190f5b…`，实机镜像 `1cd72d23` 在 `pc=fffffe0007aafc00` 返回，端到端验证通过。
- **恢复。** 两次无限重启都由用户手动进入 fastboot，写 trimmed 原厂前缀，进 Recovery 后写回完整 67,108,864 字节并校验 `2931647a…`。没有残留测试镜像。
- **RAM disk 根与 `bsd_init` 执行通过。** 用 `research/sweet-init`（16,635 B，`f5de3714…`）生成 payload（`4df6b274…`，ADT `RAMDisk=<0x1024d0000,0x8000>`、`rd=md0`）。带入口断点的 `bsd_init` 检查点（`e6d4bf7e`）返回 `pc=fffffe000776e048 x0=0`，证明带 RAM disk 的 payload 确实进入 `bsd_init`。
- **两处 30 秒等待。** `IOKitInitializeTime` 在 `0xfffffe00079ad070` 等 RTC 服务 30 秒；`IOFindBSDRoot` 在 `0xfffffe0007a41e70` 等 IOMedia 30 秒，之后才调用 `mdevadd` 创建 md0。两者与诊断 shim 的 31 秒看门狗重叠，造成此前的“无限重启”。跳过等待后，`vfs_mountroot` 返回 `x0=0`，`bsd_utaskbootstrap` 入口（`pc=fffffe000776ee8c`）与 `load_init_program` 入口（`pc=fffffe00077ee118`）均命中。
- **看门狗是诊断构建行为。** `mkentryprobe.py` 用 `WDT_AUTO_RESET` 重新武装 MT6983 的 31 秒 AP 看门狗；生产 `shim/build.sh` 在入口 `wdt_disable_raw()` 关闭它。生产镜像 `fa6607a8…`（原始等待）与 `236b9828…`（跳过 RTC/IOMedia 等待）启动后不再循环，但屏幕保持黑屏/logo，说明看门狗复位是诊断假象，真实阻塞在 console/用户态可见性。
- **当前未证明项。** 生产镜像静止且无输出；跳过 `sweet_display_init` 的 `996197e5…` 仍无文字。`load_init_program` 已到达，但 PID 1 是否执行、`/dev/console` 是否阻塞、用户态是否发生异常，仍需通过 XNU msgbuf 或串口证据确认。

## 3. 如何启动到用户态

**最短路径是先运行 RAM disk 中的最小 PID 1；这一步不需要 UFS、触摸或完整 iOS 根文件系统。** 当前 payload 已带 `RAMDisk` 与 `rd=md0`，`bsd_init` 和 `vfs_mountroot` 已在实机完成；剩余问题是执行 init 后的可见证据。

预期顺序如下：

```text
已完成：arm_init → machine_startup → kernel_bootstrap
       → vm_mem_bootstrap（vm_page / zone / vm_object / vm_map /
         kmem / vm_fault 全部返回）
       → sched_init → task/thread 初始化 → load_context
       → kernel_bootstrap_thread
       → idle_thread_create → sched_startup → thread_daemon_init
       → spllo → initialize_screen
       → 定时 IRQ / sched maintenance（sched_tick +3）
       → OSKextRemoveKextBootstrap → machine_lockdown
       → CONFIG_XNUPOST → PE_lockdown_iokit → vm_set_restrictions
       → kperf_init_early
       → bl bsd_init（当前实机到达点）

下一步：执行 bsd_init
       → 根设备 / md0 根文件系统 → load_init_program
       → EL0 的最小 PID 1 心跳并持续存活
       → Apple launchd → 系统服务 → 桌面
```

建议分成五个可验收阶段：

| 阶段 | 要做的事 | 通过标准 |
| --- | --- | --- |
| A：完成 VM（已完成） | zone/object、vm_map、kmem、vm_fault 等 | `vm_mem_bootstrap` 返回后断点命中，未发生更早异常 |
| B：调度器与 IRQ（已完成） | scheduler、task/thread、上下文切换、`spllo` 与定时中断 | bootstrap thread、`sched_startup`、`thread_daemon_init` 返回；tick 探针 `sched_tick` +3 |
| C：lockdown 与 bsd_init 前路径（已完成） | `OSKextRemoveKextBootstrap`、`machine_lockdown`、XNUPOST、IOKit lockdown、kperf | 正式 CI 内核 0084 到达 `bl bsd_init`（`pc=fffffe0007aafc00`） |
| D：bsd_init 与最小根（已完成） | 执行 `bsd_init`；用 `mkpayload.py --ramdisk` 打包静态 init，使用 mockfs/md0 | `md0` 注册、根挂载、`load_init_program` 入口命中（已完成） |
| E：进入 EL0（进行中） | 使用现有 `sweet-init.S` 和 `mkinit.py`，验证代码签名、用户栈和系统调用 | 真机输出 PID 1，`open/write/getpid/select` 正常，多个五秒心跳持续运行；当前 console 无输出，需先取得 msgbuf/串口证据 |

测试程序路径虽然叫 `/sbin/launchd`，内容是项目自己的静态 init。看到其心跳代表“用户态已跑通”，尚不代表 Apple launchd 或 iOS 已运行。该程序已处理真实 ARM64 对 SP 对齐的要求，不能随意删除这类只在硬件上暴露的修复。

有两处必须提前处理：

1. **诊断向量与正常异常的边界。** IRQ 转发已在实机证明有效，但诊断回传仍是“命中 BRK 就放弃当前 XNU 状态并返回 Linux”。EL0 的 SVC/缺页槽保持 XNU 原处理器，尚未在完整引导中触发；进入用户态前应移除诊断 relay，或确保它只拦截指定的诊断 BRK，其余异常完全按 XNU 处理。执行到 `bsd_init` 以后，内核已有更多不可回退的状态（BSD、IOKit、线程），不能默认还能无副作用地跳回 Linux。
2. **每个更深断点都要重新检查内存。** 128 MiB 的清理范围 `[0x100000000, 0x108000000)` 已覆盖到 `bl bsd_init`，但 `bsd_init`、RAM disk、文件系统和用户态会继续分配页表、缓冲区与设备内存。后续断点必须重新核对 dirty 范围、bootstrap TTBR0 页的存活和 Linux 保留区域，不能沿用“上一轮没坏”作为证明。

`vm_retire_boot_pages` 在当前 CI 内核中仍只有一条 `ret`（空实现），但 lockdown 已经通过，且 `bootstrap_pagetables` 位于 `__DATA_CONST`，不会被 `__BOOTDATA` 的释放回收。更晚的 `bsd_init`/RAM disk 分配、页表变化和向量切换仍需逐段验证；换内核后必须重新检查地址与清理范围。

## 4. 如何真正启动 iOS

在这台设备上，目标是运行真实 iOS 用户空间程序，并用移植后的 XNU 和硬件服务支持它们。工程上可分为“Apple launchd 运行”“系统服务运行”“桌面可见”“桌面可交互”四个独立里程碑。

### 4.1 用户空间和文件系统

项目现有路线选择 iPhone X 的 iOS **16.7.16 / 20H392**，使用普通 `arm64` 用户空间。这一代 A11 用户空间不要求 `arm64e` 的指针认证 ABI，适合复用现有内核兼容工作；不能仅因 MT6983 CPU 更新，就随意替换成新机型、新系统的用户空间。

根镜像需要同一版本的 OS、SystemOS、AppOS、`/usr/lib/dyld`、`/sbin/launchd` 和完整的 dyld shared cache 分片。不能只复制 launchd：libSystem 等依赖主要位于 shared cache 中。历史资产是数 GiB 级别，不适合当前包含原 Linux 的诊断 boot 镜像。原 sweet 的 fastboot 容量限制也不能直接套到 matisse。

仓库采取 **从 APFS 读取文件、重新制作大小写敏感且带日志的 HFS+ 根卷** 的路线。XNU 已有内建 HFS 支持，无需先完成 APFS 移植。`mkiosroot.sh` 整合 cryptex 文件和共享缓存链接；必须验证实际文件、权限、所有者、硬链接、符号链接以及需要的元数据，并完成文件系统检查。该脚本面向 Linux 的 FUSE/loop mount 环境，不能原样视为 macOS 一条命令可运行。

### 4.2 分阶段验收

当前实机只到达 `bl bsd_init` 调用点，下面四个阶段都还没有开始；先完成第 3 节的 `bsd_init`、最小根和 EL0。

| 阶段 | 依赖与工作 | 应拿到的证据 |
| --- | --- | --- |
| Apple launchd | 最小用户态稳定；UFS 根读取可靠；dyld/cache、Mach、pthread、签名与 entitlements 兼容 | Apple launchd 成为 PID 1，正常装载库并启动子进程 |
| 系统服务 | 可写 `/private/var`、容器目录、共享内存、系统属性、KeyStore 等兼容服务 | 核心服务连续运行，崩溃能记录与符号化 |
| 桌面可见 | IOSurface、IOMobileFramebuffer/AppleCLCD、CoreAnimation 软件绘制、持续面板刷新 | backboardd、SpringBoard 运行，画面实际出现在手机上 |
| 桌面可交互 | ST 触摸、按键、坐标映射和 HID 事件 | 点击、拖动、抬起、多指、底部手势、锁屏唤醒分别验证 |

现有补丁包含 AMFI/entitlements、AppleKeyStore stub、Sandbox、HFS、IOSurface、HID 等兼容工作，`sweet-root-tweaks.py` 包含原机型使用的 Setup、迁移、watchdog 和无硬件服务调整。应按日志逐项复核兼容性，不能把一批守护进程不再报错等同于真实硬件已经实现。

现有激活状态相关调整也不等于获得 Apple 官方激活、Apple ID、App Store 或安全服务支持。SEP、Secure Enclave 数据保护、Face ID 和 Apple 硬件信任链未移植；已有测试内核放宽了安全策略，实验设备不适合保存个人敏感资料。

### 4.3 显示是桌面阶段的额外工作

已有补丁 `0082` 解决早期 framebuffer 映射，`0083` 为 **控制台** 接入 MTK 命令模式刷新。探针已证明继承 LK 显示状态可以出图；这不等于完整冷启动面板驱动已实现。

GUI 的 IOSurface/AppleCLCD 拷贝路径也必须在每次提交后触发 matisse 刷新。只让串口控制台调用刷新，切换 GUI 并关闭控制台后可能停留在旧画面。还要处理真实 1440×3200 面板与 iPhone X 1125×2436 逻辑画布之间的缩放、裁剪或留边，并让触摸使用完全相同的变换。

先用 CPU 绘制建立可见、可交互桌面；Mali GPU、Metal/OpenGL 兼容是独立的大项。原 sweet 的帧率和启动时间不能当作 K50 Pro 的实测性能。

2026-10-31 补充：原生 1440×3200、触摸和三个实体键的实机验收已经完成，
本节其余 bring-up 描述保留历史上下文。GPU 采用独立的
[MT6983 CSF / Panthor / PanVK 路线与接口审计](matisse-gpu-plan.md)，
只借鉴 UniXNU 的分层；当前尚无 GPU 加速实测。

## 5. 如何接通 UFS

### 当前状态

Android/Recovery 已能使用 UFS；**XNU 和 shim 在 matisse 上可靠读写 UFS 尚未证实**。当前 matisse ADT 不暴露 Qualcomm 的 `sweet-ufs` 节点，并强制 `ufsrw=0`。`ufsrw=1` 只是请求写权限，不能替代控制器移植。

live FDT 的主控制器是 `ufshci@112b0000`，compatible 包含 `mediatek,mt8183-ufshci`。兼容字符串复用旧型号并不表示板子是 MT8183。旧 shim 试验没有得到可靠的持久日志；控制器接管、时钟、电源、DMA/IOMMU 等仍需分别排查，不能把某一个猜测写成已找到根因。

### 建议实施顺序

1. **先收集只读基线。** 对照当前固件的 live FDT、Recovery 驱动和相应 MediaTek 厂商源码，记录电源域、clock/reset、PHY、HCE/HCS、UTRL 地址、运行状态、doorbell、错误状态、LUN 与逻辑块大小。避免访问尚未供电的 MMIO。
2. **确定接管方法。** 优先复用 LK 已建立的链路，但必须确认请求已静止、队列可停、UTRL 新地址写入可读回。只有完成这一点才允许提交自己的命令。失败后再研究完整 MTK 初始化：时钟、电源、PHY、UIC/link startup、设备初始化与链路电源模式，不能只改 MMIO 基址。
3. **先单队列轮询，只读命令。** 依次做 TEST UNIT READY、READ CAPACITY、读取已知块和 GPT。比较 Recovery 读取的相同 LBA 数据与 SHA256；验证 GPT CRC、LUN、分区范围和块大小。不要将 sweet 的 LUN0 或 4 KiB 假设直接当成本机事实。
4. **解决 DMA 与缓存。** 验证 CAP 对地址宽度的支持、UTRD/UCD/PRDT 对齐、物理地址高 32 位、连续内存、cache clean/invalidate 和屏障。上部 RAM 超过 4 GiB；若设备使用 IOVA/IOMMU，必须明确其地址转换关系，不能默认 CPU PA 就是总线地址。
5. **接入 XNU 块设备。** 复用 `sweet_ufs.c` 的设备接口、分区边界检查和文件系统衔接，把 MTK host 部分独立出来；先保持只读。分清设备物理块与 BSD 512-byte sector 接口。
6. **最后验证写入与根镜像。** 在明确批准的、备份充分的测试区域做限界写入、读回、flush 和恢复测试，再验证文件系统一致性与异常重启。只有达到这些标准，才考虑单独授权将 iOS 根写入既有 `userdata`；不改 GPT，不碰其他 LUN/引导区。

### 代码复核发现的待修问题

本次阅读 `shim/ufs.c` 还发现三个具体问题，应在复用该实现前修正并验证；它们不构成旧接管失败的唯一原因：

- `gpt_entries()` 用 `be32` 读取 GPT 的 entry LBA/entry count；GPT 使用小端，其中 entry LBA 是 64 位。
- SCSI 写命令的 Command UPIU 没有设置 W 数据方向标志；当前 `cmd[1]` 只处理读方向。
- 超时按固定 19,200,000 ticks 估算一秒，与本机 13 MHz 不符；应使用实际计时器频率。

这些问题位于 shim 的 UFS 实现，不能不经检查就推断 XNU 的独立 UFS 实现存在完全相同的问题。当前 `ufs_mark`、`ufs_log_write` 等都不能当作已验证的日志基础设施。

还有一个结构问题：现有 XNU 代码在 UFS 初始化成功后才调用触摸、按键、USB 和部分日志初始化。应把这些移到合适的平台/IOKit 启动阶段，使 RAM disk 启动也能单独测试它们。

## 6. 如何接通触摸

### 更正硬件身份

旧 NOTES 把 `fts@0` 写成 FocalTech，本次以真机绑定和日志更正：

| 项目 | 已读到的证据 |
| --- | --- |
| live compatible | `st,spi` |
| Recovery 驱动 | `spi6.0` 绑定 `fts`，加载 `fts_touch_spi.ko` |
| 固件名 | `st_fts_L11.ftb`，limits 文件名含 `stm_fts` |
| 总线 | SPI6，控制器 `0x11016000`，CS0，8 bits，mode 0，日志最大速率 12 MHz |
| GPIO | DT 中 IRQ GPIO8、reset GPIO3；GPIO编号不是 GIC INTID |
| 坐标 | 日志 Touch Resolution 为 14399×31999；DT 声明 14400×32000 超分辨率范围 |

证据支持按 **ST FTS** 驱动路线移植；具体芯片型号和协议版本仍应从芯片 ID、对应源码和现有固件确认，不能只靠 `fts` 名称推断。Recovery 日志能够读取固件版本和系统信息，同时出现固件文件加载 `-2`；这不等于芯片没有运行固件，也不代表必须立即刷写固件。

### 实施与验收

1. 从相匹配的厂商驱动提取 SPI 帧格式、dummy bytes、命令/事件 FIFO、reset 和供电时序。DT 记录的 `avdd/vdd` 和 MT6373 regulator 依赖需要核实，不能复用 Qualcomm RPMh。
2. 先保持当前可用固件与校准，完成 MTK SPI 最小收发；读芯片 ID/系统信息，连续重复并验证一致性，再启用触摸扫描。不要将自动固件升级、工厂测试或校准重写带入初版驱动。
3. 先轮询事件 FIFO，记录按下、移动、抬起和 contact ID；随后接入 GPIO/EINT 中断，处理清状态、排空 FIFO、超时与异常复位。
4. 把原始事件转为现有 HID digitizer 服务；复用 HID 上层接口，替换 `sweet_touch.c` 的 GENI/Goodix 底层。
5. 根据实际坐标范围做旋转、轴交换、缩放、裁剪/留边，再映射到 iOS 逻辑画布。不能把 14400 范围直接当作 1440 像素，也不能保留原 sweet 的 1080×2400 常量。
6. 验收四角、中心、连续拖动、抬起、多指、底部 Home 手势以及锁屏唤醒。能点击不代表手势完整，必须排查事件生命周期、边缘过滤与 HID 服务属性。

第一阶段无需触摸即可进入最小 PID 1；真实触摸是“iOS 可交互”阶段的要求。

## 7. 如何接通 USB

**Recovery 有 adb 和 LK 有 fastboot，只证明它们自己的 USB 栈可用；XNU 需要自己的 USB 驱动。** 这里优先让手机充当接到电脑上的 USB device。xHCI 的主机模式是另一条路径，不能用来直接代替 gadget/device 控制器。

本机为 MTU3/SSUSB，记录的资源包括 `0x11201000` 和 `0x11200000`。真正实现时要按 live FDT 的各 `reg`、`reg-names`、PHY、clock、power 和端口角色解释这些窗口，不能只拿两个基址照搬驱动。现有 `0072` 至 `0081` 中的 sweet USB 工作面向 DWC3，无法靠 `sweetusb=1` 在 MediaTek 上启用。

建议按以下顺序做：

| 阶段 | 工作 | 验收 |
| --- | --- | --- |
| U0：资源与角色 | 核实 MTU3 device 路径、PHY、时钟、电源、VBUS、Type-C/角色控制 | 控制器可读，device 角色稳定，无总线异常 |
| U1：最小枚举 | 完成 EP0、描述符、SET_ADDRESS、SET_CONFIGURATION、reset | 主机稳定识别正确描述符，多次插拔可恢复 |
| U2：调试通道 | 做 bulk IN/OUT 或合适的串口类；初期选择较简单的 FIFO/PIO 路径（若硬件支持），之后再加 DMA/QMU | 双向校验数据与连续内核日志，不丢包、不锁死 |
| U3：网络 | 移植 CDC ECM 类逻辑、内核网络接口和数据包路径 | 双向 ping；再验证 IP、路由、DNS、NAT 和较长传输 |
| U4：系统服务 | 根据需求增加文件传输、远程 shell 或相应用户态服务 | 服务长期稳定、断线重连正常 |

DWC3 的 TRB/endpoint 寄存器实现不能直接复用到 MTU3；USB 类协议与部分 ECM 网络逻辑才有复用价值。枚举、链路 up、ping 通和能上网是不同的验收点。

若使用 DMA/QMU，同样要处理 IOMMU/总线地址、缓存一致性、描述符对齐和中断。端口方向与 VBUS 还可能依赖 Type-C/充电芯片，不能照抄原 Qualcomm 驱动的 VBUS override。ADB、usbmux/lockdown 也不会在 USB 枚举后自动出现，它们需要另外的用户态协议实现。

USB 日志能显著减少后续对屏幕和断点回传的依赖。定时 IRQ 与调度维护已经在正常 XNU 向量下通过，最小 USB 日志可以作为 `bsd_init`/RAM disk 之后的优先项，再扩展 ECM 网络。

## 8. 推荐执行顺序与其他注意事项

| 优先级 | 下一项 | 完成标志 |
| --- | --- | --- |
| 1 | VM、调度器、定时 IRQ、lockdown 与 kperf 前路径（已完成） | 正式 CI 内核 0084 到达 `bl bsd_init` |
| 2 | 执行 `bsd_init` 与最小 RAM disk 根（当前优先级最高） | `md0` 注册、根挂载、`load_init_program` 执行 |
| 3 | EL0 最小 PID 1 | PID 1 多次心跳，`open/write/getpid/select` 可重复 |
| 4 | 稳定屏幕日志或 MTU3 最小 USB 日志 | 能连续观察真实内核故障，不依赖仅显示 logo |
| 5 | MTK UFS 只读、受控写入与根镜像 | 块数据校验、文件系统验证通过 |
| 6 | Apple launchd、dyld/cache 与核心服务 | 真实 iOS 用户空间持续运行 |
| 7 | GUI 帧提交刷新、ST 触摸和 MTK 按键 | 可见、可交互的 SpringBoard |
| 8 | USB 网络、电源/温控、多核及更多外设 | 每项独立测试后启用 |

以下是与本项目直接相关的约束：

- **设备恢复：** 每轮新 boot_a 写入单独确认。失败时先由用户进入 fastboot，写已验证的恢复前缀，进入 Recovery 后再写完整 64 MiB 并全量读回校验。只刷前缀曾遗留测试数据，不能算恢复完成。
- **日志与证据：** 优先同次启动日志。`adb exec-out dd` 曾静默短读，分区校验使用设备临时文件再 pull，并同时检查长度和 hash。直接 log_store、expdb 或 UFS 日志不是现成可靠通道。
- **内存：** 当前 XNU 配置的上部窗口是 `0x100000000..0x22e000000`，约 4.72 GiB；它不代表已经压力验证所有 RAM。后续内存扩展需逐个避开 secure/carve-out、framebuffer、回传及 DMA 保留区。
- **时钟和中断：** 使用本机 13 MHz、虚拟计时器 INTID27，避免复用 sweet 的 19.2 MHz/INTID19。GPIO编号、Linux IRQ 和 GIC INTID 不能混用。
- **多核与 CPU 驱动（2026-10-25 实机验证通过）：** matisse ADT 现在声明 8 个 CPU 节点（cpu@000..300 = A55，cpu@100..200 = A78，reg/MPIDR 0x000..0x700），每个节点的 compatible 以 `qcom,kryo470` 开头，因此 SweetCPU 能匹配并走既有 PSCI CPU_ON + initCPU/SGI1 路径；`cpus=N` 选择 1..8 的前缀（默认 8）。8 核 probe 的 `vfs_mountroot` 断点返回 x0=0，且 `kperf_init_early` 的 `ml_wait_max_cpus` 只在 8/8 核完成 initCPU + SGI1 后才被放行，证明 0x100..0x700 七个从核的 PSCI、GIC redistributor、SGI 与缓存初始化均可用。CPU_OFF/quiesce 与异构簇上报仍未实现。
- **per-CPU 中断探针（2026-10-25 实机）：** `tools/xnu_smp_irqprobe.py` 在 mountroot 检查点跳入早期向量槽 14 的 cave，等待 2 s 后读取 `CpuDataEntries` 中每核的 `ipi_cnt`（`cdp+0x228`）与 `timer_cnt`（`cdp+0x238`）。实机 banner 返回 IPI 掩码 `0xff`（8/8 核都有中断入口活动）和定时器掩码 `0x03`（仅 CPU0/1）。这与 XNU arm64 的 tickless 设计一致：`SetIdlePop()` 只在 `rtcPop` 存在真实未来 deadline 时 arm vtimer，空闲且无调度线程的从核累计 tick 计数保持 0；CPU1 的计数是从核 vtimer 投递的首个证据，CPU2-7 在调度负载下的直接 vtimer 证据仍待更晚检查点验证。
- **电源与外设：** 按键走 MTK PMIC/SPMI；电池、充电、热管理、挂起恢复均未完成 XNU 移植。先短时可观测测试，再考虑长时间运行；不要把静态电量服务当作真实充电/温控。
- **后续大项：** Wi-Fi、蓝牙、基带、音频、摄像头、传感器、GPS、GPU、休眠唤醒都需要独立驱动/固件/用户态接口。桌面亮起不会自动补齐这些功能。
- **写入范围：** iOS 根的预定位置是现有 `userdata`，未来写入仍需当次明确确认；不修改 GPT，保留 bootloader、vendor_boot/Recovery、modem、persist 和校准备份。
- **构建管理：** 内核改动先单文件交叉编译，再通过 `gh` 使用 Actions 构建，记录运行 ID、提交和产物 hash。镜像、设备 dump、序列号、Apple 资源保留在忽略目录。完成的源码/文档更新提交，避免混入未验证的旧修改。

## 9. 本轮可核对的构建、恢复和交接信息

**内核与 CI。** 最新成功构建为 [GitHub Actions 39828405447](https://github.com/Jinsens/ios-sweet/actions/runs/39828405447)，提交 `b616374`，包含补丁 `0084-sweet-single-cpu-max-cpus.patch`。首次在 `main` 上的 dispatch（`39826038020`）在任何 step 开始前被取消；改用 `codex/matisse-xnu-screen-log` 重新 dispatch 后成功。

```text
kernel: xnu/out/ci-39828405447/kernel.development.sweet
SHA256: 28190f5b4c274b4d5c1501f08b776873c5a9190ec67b74021bd4f42b795267f2

payload: shim/out/matisse-xnu-ci39828405447.payload
SHA256: e39237a808568658c363b8d10fbac9916b4093c2f8b0992cebfbc870c13f887c

永久补丁验证镜像: shim/out/entryprobe-el1-bsd-init-0084-brk.img
大小: 26,562,560 bytes
SHA256: 1cd72d232491a871296d611720a8ac55774f4c743a286131841b2dff1da93599
断点: VA fffffe0007aafc00 / PA 0x101aafc00（bl bsd_init）
同次启动记录:
stage=87 fault=1 esr=f2005357 far=0 pc=fffffe0007aafc00
x0=0

完整恢复备份:
backup/recovery-20261021/boot_a-live-20261021.img
大小: 67,108,864 bytes
SHA256: 2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1

trimmed 恢复前缀:
backup/boot_a-stock-trim.img
大小: 20,873,216 bytes
SHA256: fe6e8fbf321ea542eb060efcda27b70ae96065e82cc871d4c71082b7268c220d
```

**RAM disk 最小根（2026-10-23 主机侧准备，未刷机）。** 使用同一 CI 内核、`shim/out/matisse.adt` 和由 `tools/sweet-init.S` + `tools/mkinit.py` 重建的 `research/sweet-init`（SHA256 `f5de3714…`）。`rd=md0` 经 `platform_cmdline` 保留，命令行 135 B。RAM disk 段位于 VA `0xfffffe00084d0000` / PA `0x1024d0000`，大小 32 KiB；ADT 的 `/chosen/memory-map/RAMDisk` 为 `0x1024d0000/0x8000`，ADT 与 boot_args 随后放在 `0x1024d8000`/`0x1024dc000`，全部在已验证的 128 MiB 清理范围内。

```text
payload: shim/out/matisse-xnu-ramdisk-init.payload
大小: 16,622,400 bytes
SHA256: 4df6b274603e3897e9699bb7bc11791556f1067868e772a0fdf1592d5354f9b9

用户态启动镜像（无断点）: shim/out/entryprobe-el1-ramdisk-init.img
大小: 26,562,560 bytes
SHA256: b337bfbf86bbe62c769bf6521df0331f65e7cf7d0c4d9973d83b0ae0cafcbe75

bsd_init 返回检查点: shim/out/entryprobe-el1-ramdisk-bsdinit-return-brk.img
SHA256: 9a8c43dbe6b2c13bf9ad2136c21320bc7bf23df878759b63bd4b7d57d40c1821
断点: VA fffffe0007aafc04（bl bsd_init 之后）

load_init_program 检查点: shim/out/entryprobe-el1-ramdisk-load-init-brk.img
SHA256: b4af6752d90b82a46b814de428f92e1eeabc39073f15dfdf1a44c6bcc68928e8
断点: VA fffffe00077ee118
```

三种镜像均重新解包并核对了嵌入的 `SWEETXNU` payload SHA、init 的 `MH_MAGIC_64`、ADT `RAMDisk` 对、命令行长度，以及“只有检查点镜像含一个 `BRK #0x5357`”。44 项工具测试通过。设备仅做只读核对：Recovery、root ADB、slot `_a`，`boot_a` 仍为 `2931647a…`；本轮未写入任何分区。刷机仍需单独确认。

关键检查点镜像（均为 26,562,560 bytes；命中后自动返回 Recovery，随后全量恢复并校验）：

| 检查点 | 镜像 SHA256 前缀 | 记录 PC |
| --- | --- | --- |
| bootstrap thread | `154449c1` | `fffffe0007aaf74c` |
| `sched_startup` 返回 | `c1859ef9` | `fffffe0007aaf7d4` |
| `thread_daemon_init` 返回 | `f16c296d` | `fffffe0007aaf80c` |
| `spllo` / `initialize_screen` 返回 | `ff8e21bf` | `fffffe0007aaf9ec` |
| 定时 tick 探针 | `80c8f80f` | `fffffe000748d744`（x0=3） |
| `machine_lockdown` 返回 | `f68a28a8` | `fffffe0007aafb54` |
| NOP-kperf 诊断 | `14bef24d` | `fffffe0007aafbe0` |
| payload max_cpus 修复 | `8783158b` | `fffffe0007aafbe0` |
| 正式 CI 内核 0084 | `1cd72d23` | `fffffe0007aafc00` |

RAM-disk/bsd_init 检查点（诊断镜像，命中后返回 Recovery）：

| 检查点 | 镜像 SHA256 前缀 | 记录 PC |
| --- | --- | --- |
| `bsd_init` 入口 | `e6d4bf7e` | `fffffe000776e048`（x0=0） |
| `kauth_init` 返回 | `2cd7b8da` | `fffffe000776e0bc` |
| `kmem_suballoc` 返回 | `1a7591e5` | `fffffe000776e4a4` |
| `bsd_bufferinit` 返回 | `20ccaae1` | `fffffe000776e4b0` |
| RTC 绕过后 `vfsinit` 返回 | `dd2ee108` | `fffffe000776e4b8` |
| `IOKitBSDInit` 返回 | `2f2a4873` | `fffffe000776e558` |
| `vfs_mountroot` 返回 | `8db80188` | `fffffe000776e63c`（x0=0） |
| `bsd_utaskbootstrap` 入口 | `59d7ae2f` | `fffffe000776ee8c` |
| `load_init_program` 入口 | `56b5080e` | `fffffe00077ee118` |

生产镜像（无诊断 relay、看门狗关闭）：

| 镜像 | SHA256 | 结果 |
| --- | --- | --- |
| 原始等待 | `fa6607a8` | 静止黑屏/logo，未循环 |
| 跳过 RTC/IOMedia 等待 | `236b9828` | 静止黑屏/logo，未循环 |
| 再跳过 `sweet_display_init` | `996197e5` | 仍无文字 |

失败记录（均已恢复，未残留测试镜像）：

- slot-4-only 的 `1787a791`：BRK 走 EL1t slot 0，未返回并循环重启；改为双槽 stub 后通过。
- `bsd_init` 大跳的 `7a5b60b5`：未返回并循环重启；排除 XNUPOST 后仍失败。
- XNUPOST-skip 的 `ce02efbf`：未返回；随后用 NOP-kperf（`14bef24d`）锁定 `kperf_init_early()`。
- 所有失败恢复均按：用户手动 fastboot → 写 `boot_a-stock-trim.img` → 进 Recovery → 写完整 64 MiB → 全量读回校验 `2931647a…`。

证据目录（gitignored）：

```text
research/matisse/20261023-sched-startup/
  sched-startup-dmesg.txt
  thread-daemon-dmesg.txt
  spllo-dmesg.txt
  tick-dmesg.txt
  lockdown-dmesg.txt
  nokperf-dmesg.txt
  maxcpu-dmesg.txt
  ci0084-dmesg.txt
  *-written.img / *-restored.img
  prepared-build.txt
  skip-xnupost-build.py
  nokperf-build.py
  maxcpu-fix-build.py
  ci-39828405447/（kernel、buildtree 与 SHA256SUMS）
```

关键提交：`5f3ba55` 选择性诊断向量；`42d6582` EL1t/EL1h 双槽修正；`8ddef0a`、`90c4084` 调度器检查点与通过记录；`3235c74` thread_daemon；`4a930d1` spllo；`d90dcf8` 定时 IRQ；`eaed2c0` lockdown；`8c353e9`、`a798c4c` XNUPOST/kperf 隔离；`6287cb8` 单 CPU max_cpus 实机通过；`b616374` 永久补丁 0084；`5321eae` 最终交接。

本轮结束时设备在 Recovery（root ADB，slot `_a`），`boot_a` 已从完整备份写回并校验 `2931647a…`，没有残留测试镜像；未写 `userdata`。下一步是取得 XNU msgbuf 或串口证据，确认 `load_init_program` 之后 PID 1 的实际执行状态。RAM disk 最小根和 `bsd_init`/`load_init_program` 检查点已准备好（见上一节），但尚未刷入。下一步是在获得当次确认后刷入无断点的 `entryprobe-el1-ramdisk-init.img`，观察面板上的 `load_init_program`、PID 1 与 5 秒心跳；失败时依次改用两个检查点定位。先拿 EL0 PID 1，再谈 Apple launchd 与桌面。不要直接刷 iOS 根镜像。
