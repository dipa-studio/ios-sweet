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

## 2339：复位入口的两个外设写（离线准备，2026-11-04）

2338 排除了时钟问题之后，剩下的问题是 MCU 到底停在哪。把真实固件的
向量表和复位入口反汇编出来，答案变得具体了。

### VA 0 是标准 Cortex-M 向量表

```
VA 0x0000  02040000   初始 SP = 0x02040000（0x02000000 段的顶端）
VA 0x0004  010018ed   Reset_Handler = 0x010018ec（Thumb 位）
VA 0x0008  010019b1   NMI/HardFault/MemManage/BusFault/UsageFault 共用
```

这确认了 `0x010018ec` 就是复位入口，之前 2335/2336 的检查点没有打错位置。

### 复位入口前几条指令

```
010018ec  cpsid i
010018ee  ldr  r0, [pc, #0x98]     ; r0 = 0x40022000
010018f0  mov.w r1, #0xb
010018f4  str  r1, [r0]            ; <-- 第一个 MCU 外设写
010018f6  ldr  r0, [pc, #0x94]     ; r0 = 0x40022004
010018f8  mov.w r1, #0x7
010018fc  str  r1, [r0]            ; <-- 第二个 MCU 外设写
010018fe  ldr  r0, [pc, #0x90]     ; r0 = 0xE000ED24 (SCB SHCSR，内核私有)
...
01001906  ldr  r0, [pc, #0x8c]     ; r0 = 0x0203F000
01001908  msr  psp, r0
0100190c  mov.w r0, #2
01001910  msr  control, r0         ; 切到 PSP 栈
01001918  ldr  r0, [pc, #0x7c]     ; r0 = 0x40003034，外设读
```

关键在于：**MCU 在碰任何私有内存之前，先对 `0x40022000/0x40022004`
做两次写。** 如果那个外设窗口不应答，写就会挂住总线，MCU 停在第五条指令，
此后什么都不会发生——正好符合“`MCU_STATUS=1`、无 fault、但 `version=0`、
入口检查点不出现”的全部观测。

这也解释了 2334：它把 20 字节入口整个替换成自循环 stub，**顺带跳过了
这两个写**，所以它执行了；而 2335/2336 把控制流重新接回原始代码，就再没
有下文。

### 2339 的做法

不替换任何指令，只改两个字面量：

| 文件偏移 | 原值 | 新值 | 含义 |
|---|---|---|---|
| `0x281c` | `0x40022000` | `0x04000ffc` | 第一条 `str` 的目标 |
| `0x2820` | `0x40022004` | `0x04000ffc` | 第二条 `str` 的目标 |

两个常量在整份固件里各只出现一次，因此只被这两条 `ldr` 使用；
补丁后固件长度不变、代码段一字未改（入口首字仍是 `0x4826b672`）。

于是 `shared+0xffc` 变成一个执行进度字：

| 值 | 含义 |
|---|---|
| `0` | 复位入口一条都没执行 |
| `0xb` | 执行了第一条写，卡在第二条之前 |
| `0x7` | 两条写都执行了（并且绕开了外设） |

### 这次试验的两种结局都有价值

- **`0x7` 且 `version` 变成 `0x01010000`** —— MCU 真正跑起来了，global
  interface 就绪，CSF 阶段可以继续往下走。
- **`0` 或 `0xb`** —— 说明卡点不是这两个外设写，而是更早的位置（取指、
  或者 `cpsid`/`ldr` 就已经不对），那就要回头查 MCU 的取指通路。

`0x7` 但 `version` 仍为 0 也是有信息量的：说明外设写不是全部原因，
固件在更后面的私有内存或中断初始化处停住。

## 2339 实测结果（2026-11-04）

镜像 `fb059ab3…`，一次授权试验。runner 这次走了新加的 fastboot CLI 兜底，
`boot_a` 自动恢复为 `2931647a…`，设备回 Recovery，无残留。

```
mcu_store_progress   none      进度字 = 0
entry_marker_after   0
version              0
mcu_status           1
job_raw              0
```

**两个字面量改到 `shared+0xffc` 之后，第一条 store 仍然没有落地。**

### 这条否定了什么

2334 的 stub 本身就用 `ldr` 从代码页取字面量并成功写进 `shared+0`，
所以 **MCU 的数据读取和 store 都是通的**。2339 失败不可能是"数据通路不行"。

剩下的解释只有两类：

1. MCU 在第一条 store 之前/之后就被别的东西卡住了，写入还留在缓冲里；
2. `shared+0xffc` 这个位置本身收不到写（2336 也是这个位置，同样为 0）。

而且入口在两条 store 之后紧接着还有一次外设**读**：

```
0x1918  ldr r0,=0x40003034
0x191a  ldr r4,[r0]        <-- 读不到就同样挂死
```

## 2340：一次试验分开这两种可能

同样不替换指令，改三处字面量：

| 字面量 | 原值 | 新值 | 目的 |
|---|---|---|---|
| `0x281c` | `0x40022000` | `0x04000000` | 第一条 store 写版本字（2334 验证过可写） |
| `0x2820` | `0x40022004` | `0x04000ffc` | 第二条 store 写进度字 |
| `0x282c` | `0x40003034` | `0x04000ff8` | 外设读改成读共享页（读回 0，顺带跳过 0x03800000 拷贝） |

读数含义：

| `version` | `entry_marker_after` | 结论 |
|---|---|---|
| `0` | `0` | 代码根本没跑到第一条 store |
| `0xb` | `0` | 第一条执行了，`0xffc` 确实收不到写 |
| `0xb` | `0x7` | 两条都执行了，之前是卡在外设读 |
| `0x01010000` | 任意 | **MCU 启动了** |

### 顺带发现：0x03800000 未映射

入口在 `r4 = *(0x40003034) & 0x80` 非零时，会从 `0x03800000` 往 `0x02000000`
拷一段初始化数据。而 `0x03800000` 不在固件的任何段里。如果那个外设读返回的
bit7 是 1，MCU 会去读一个未映射地址。2340 把这次读改成读共享页的 0，
r4 变成 0，正好跳过这条路径。

## 2340 实测结果：MCU 确实在执行（2026-11-04）

镜像 `4e801cc5…`，一次授权试验，`boot_a` 自动恢复为 `2931647a…`。

```
version              11  (0xb)   <-- 第一个 store 写入的值
version_before        0
features              0
private_early_after   0
mcu_store_progress    none
entry_marker_after    0
mcu_status            1
job_raw               0
```

### 这是第一次拿到 MCU 执行的实证

`csf_boot.o` 在 2339 与 2340 之间**逐字节相同**，唯一差别就是固件里那两个字面量。
所以 `version` 从 0 变成 `0xb`，只能是 MCU 执行了 `0x010018f4` 那条
`str r1,[r0]`（r1 = `0xb`，r0 = `0x04000000`）。

**MCU 在取指、在解码、在向共享页写数据。** 这条否定了“MCU 死了”的所有说法。

### 同时它把问题精确到一个字

同一个 `str` 指令、同一个 4 KB 页（`0x04000000..0x04000fff`，PA `0x40110000`）：

| 目标 | 结果 |
|---|---|
| `shared+0x000` | `0xb` 落地 |
| `shared+0xffc` | 仍然是 0 |

而 2335 / 2336 / 2337 / 2339 的**全部入口检查点都放在 `0xffc`**。这就是它们
一致读 0 的原因 —— 未必是 MCU 没跑到，可能是那个字根本不收写。

2334 之所以“唯一成功”，也是因为它写的是 `shared+0`。

### 2341：把这个字单独隔离出来

只动第二个 store，往页内挪一个字：

| 字面量 | 原值 | 新值 | 目的 |
|---|---|---|---|
| `0x281c` | `0x40022000` | `0x04000000` | 第一个 store，写 `0xb`（已验证可写） |
| `0x2820` | `0x40022004` | `0x04000004` | 第二个 store，写 `0x7` 到 `features` 字 |
| `0x282c` | `0x40003034` | `0x04000ff8` | 外设读改读 0，跳过未映射的 `0x03800000` 拷贝 |

`features` 本来就是报告里的字段，所以 ABI 不动。判读：

| `version` | `features` | 结论 |
|---|---|---|
| `0xb` | `0x7` | 整页可写，**只有 `0xffc` 坏** → 换检查点地址重新测入口 |
| `0xb` | `0` | 第二个 store 根本没执行 → 卡点在两条 store 之间 |
| `0x01010000` | 任意 | **MCU 启动** |

## 2341 实测结果：整页可写，只有 0xffc 那个字是死的（2026-11-04）

镜像 `3a098759…`，一次授权试验，`boot_a` 自动恢复 `2931647a…`。

```
version     11   (0xb)   第一个 store
features     7   (0x7)   第二个 store，写的是同页的 +0x004
```

**两条 store 都执行了，而且写的是同一页的相邻两个字。** 于是：

- `_shared + 0x000` 可写
- `_shared + 0x004` 可写
- `_shared + 0xffc` **不可写**（2336 / 2337 / 2339 的检查点全部在这个字上）

2335–2339 关于"入口标记缺失"的结论，从此不能当作"MCU 没跑到"的证据。

### 顺带排除了两个猜想

`0x010019a0`（`0x03800000`）和 `0x01001934`（`0x0302bc78`）都**不在任何段里**。
所以真实外设 `0x40003034` 的 bit7 必须是 0，否则厂商固件自己在
`ldrb r1,[0x0302bc78]` 处就会取指失败。也就是说 2340/2341 把这次读
强制成 0，**恰好复现了硬件行为**，没有改变固件逻辑。

### 入口代码的完整形状

```
010018ec  cpsid i
010018ee  ldr r0,=0x40022000 ; mov r1,#0xb ; str r1,[r0]   <- store1
010018f6  ldr r0,=0x40022004 ; mov r1,#0x7 ; str r1,[r0]   <- store2
010018fe  ldr r0,=0xE000ED24 ; mov r1,#0x70000 ; str r1,[r0]  SHCSR：打开三个 fault
01001906  ldr r0,=0x0203F000 ; msr psp,r0
0100190c  mov r0,#2 ; msr control,r0 ; isb
01001918  ldr r0,=0x40003034 ; ldr r4,[r0] ; and r4,#0x80
01001922  bl 0x01003126        <- MPU 初始化（写 MPU_RBAR/RASR）
01001926  bl 0x010019d8        <- 写 0 到 0xE000ED84
0100192a  bl 0x010019e2        <- I-cache 失效 + 置 CCR 位17
0100192e  bl 0x01001a2a
01001932  cbz r4, 0x01001982
01001982  b.w 0x01002aec       <- 进固件主体
```

结论：卡点在 `store2` 之后、固件主体写 `0x0202c934` 之前。剩下的最大未知量是**真实外设写会不会挂**。

## 2342：只测真实外设

只改第二个 store（→ `shared+4`），把第一个 store（`0x40022000`）和外设读
**原样保留**：

| `version` | `features` | 结论 |
|---|---|---|
| `0x01010000` | 任意 | **MCU 启动** |
| `0xb` | `0x7` | 真实外设接受写入、执行到 store2 → 卡点在后段 |
| `0xb` | `0` | 写 `0x40022000` 就挂了 → 外设需要 AP 侧先上电 |
