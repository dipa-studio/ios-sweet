# matisse GPU 路线与证据边界

更新：2026-11-09。目标板是 Redmi K50 Pro / matisse / MT6983，
不是 sweet / SM7150，也不是 UniXNU 的 SM8550。

## 当前基线

MCU 卡点已取得实机突破。2425 启动未经修改的厂商 CSF 固件，2426 完成
全局配置握手：`GLB_VERSION=0x01010000`，新 `JOB_IRQ=0x80000000`，
`REQ/ACK=0x40e`，8 个组、stride160；MMU 无故障，停止和复位成功。
实际 GPU_ID 是 `0xa8620004`。详见 [2026-11-09 实测](matisse-gpu-20261109.md)。

关键差异是启动前增加 MT6983 厂商诊断路径中的 EMI/GALS/idle 寄存器读取。
2423 两次和2424 的受控 MCU 读写均成功；2424 补回旧 PDC/SLC 读取后仍通过。
读取副作用、延迟和启动状态的因果关系仍在隔离，不能把它解释成已知硬件勘误。
固件内容没有修改，未改 GPU 电压/频率。最新可复现镜像配置是2426。

内存与固件验收目前覆盖独立 shim 内的4 KiB GPU 页表、共享区、固件启动及
全局协议。XNU 内的常驻 GPU 生命周期、通用 BO/VM、CSG/CS 调度、任务提交、
fence 和 GPU 绘制尚未实现。现有显示仍走 IOSurface/AppleCLCD/framebuffer。
设备运行/恢复状态以 `NOTES.md` 顶部 ACTIVE 交接为准。

参考源码已固定 Linux `7475ea8b58616b33c04afb976cf0fbaad9dd63fb`、
Xiaomi rubens-s-oss `270b84910b941bf75490fccdb5fb2b3021dd7cbf` 和 OnePlus
MT6983 `ff51a39c66a87f91d870bfff1611e2b36371c8a4`。关键平台文件跨厂商一致。

## 架构选择

可以借鉴 UniXNU 的分层，但不能把 Adreno740 / Turnip / GMU 后端
改几个地址后移到 MT6983。Mali 的命令提交、固件、页表、缓存一致性
和平台电源管理都需要自己的实现。

```text
iOS 16.7.16 / CoreAnimation / Metal
  -> 与本机系统 ABI 匹配的 Metal 用户态实现
  -> AIR / SPIR-V 转换（候选复用，尚未验证）
  -> Mesa PanVK（Mali Vulkan 用户态）
  -> Darwin 适配层 + XNU 用户客户端
  -> BO / GPU VA / VM / CSF 队列 / 同步 / 故障处理
  -> Mali GPU + MT6983 平台电源、时钟和固件
  -> 线性 IOSurface
  -> 现有 AppleCLCD / framebuffer / 面板刷新
```

本机 GPU_ID 和 CSF 固件 ABI 已实测，以 Panthor / PanVK 的 CSF 路径
继续推进 Mali-G710。
不把 JM / Panfrost 内核路径作为默认，不引入 Adreno 的 PM4、
GMU、RPMh GPU 投票或 A740 固件。

截至本轮读取的 Mesa 官方支持表列出 G310/G610（v10）和
G615/G715（v11），没有列 G710。不能据此断言 G710 完全不受支持，
也不能把 G610 的 Vulkan 认证当作 G710 的保证；需核对选定 Mesa
版本的 GPU 型号表、勘误和固件要求，并独立实测。

“兼容 Linux ioctl”目前只是候选方案。必须先列清 PanVK 实际依赖的
drm、mmap、syncobj、dma-buf 和 VM/队列语义，再选择实现兼容 ABI
还是在 Mesa 增加 Darwin KMD 后端。仅复制 ioctl 编号不足以运行。

### 第一版接口审计矩阵

以下以 Linux v6.12 Panthor UAPI 为明确参考，不是已实现的 XNU 接口。
Mesa 主线后端另有更新的 ioctl；后续必须固定 Mesa 提交再确定兼容范围。

| 接口组 | 参考行为 | XNU 侧需要补齐 |
| --- | --- | --- |
| DEV_QUERY | 查询 GPU、CSF、时钟等属性 | 由实际硬件/固件生成结果；不能伪造兼容设备 |
| BO_CREATE / BO_MMAP_OFFSET | GEM BO 与 CPU 映射 | 有界分配、进程隔离、16 KiB CPU 页与 GPU 页映射、释放 |
| VM_CREATE / VM_BIND / VM_GET_STATE | 独立 GPU 地址空间和 bind 操作 | 页表、地址范围、异步依赖、TLB 与故障状态 |
| GROUP_CREATE / GROUP_SUBMIT / GROUP_GET_STATE | CSF 调度组、队列和任务提交 | 固件握手、队列内存、doorbell、IRQ、抢占/超时与复位 |
| TILER_HEAP_CREATE / DESTROY | tiler heap 上下文 | 堆分配、增长/耗尽处理、生命周期与安全回收 |
| DRM syncobj / timeline | VM bind 和队列提交的等待/完成依赖 | 有界等待、唤醒、错误传播、进程退出后的引用清理 |
| dma-buf / PRIME / sync_file | 跨进程 BO 与显式同步共享 | IOSurface 的内存所有权、句柄传递与 fence 适配 |
| 用户 MMIO / flush ID | 只读 flush-ID 页映射，辅助用户态缓存操作 | 16 KiB 页面内的寄存器隔离；不可顺带暴露可写控制寄存器 |

最后一项尤其不能照搬 Linux 的 4 KiB 隔离假设：需要审查物理
寄存器布局，无法安全映射时改成内核查询或其他受控传输。

## 分阶段验收

| 阶段 | 工作 | 必须取得的证据 |
| --- | --- | --- |
| 0：只读基线 | 核对 live DT、驱动配置、GPU 型号、固件名/版本、GPUEB、保留内存和电源域 | 来源、大小、hash、配置；源码推断与硬件读数分列 |
| 1：接口审计 | 固定 Mesa/PanVK 和参考 KMD 提交，列出平台、固件、内存、同步和 Darwin 依赖 | 接口矩阵与 16 KiB XNU / GPU 页粒度方案；尚无上电操作 |
| 2：受控探测 | 独立、默认关闭的 XNU 探针；先核实电源/时钟所有权，再读 GPU_ID | 本次启动读数与超时/错误日志；不能访问未供电 MMIO |
| 3：内存与固件 | 有界 BO、GPU VA、页表与缓存维护；CSF 固件握手、IRQ 和故障处理 | CPU/GPU 双向数据校验、固件 ABI、异常与释放路径 |
| 4：最小提交 | 单队列、单任务、完成通知与有界 fence 等待 | GPU 写回测试图/缓冲区、结果校验；失败不会挂死桌面 |
| 5：用户态 | PanVK Darwin 后端或经过审计的兼容 ABI；先离屏验证 | 枚举设备、Vulkan 离屏 clear / triangle / 同步与回读 |
| 6：显示与 Metal | IOSurface 共享、格式/stride、fence，再验证 AIR / Metal / CoreAnimation | 物理屏幕和 GPU 完成记录；保留软件绘制回退 |

初期使用线性 BGRA 表面；不要求面板或现有 framebuffer 直接消费 AFBC。
必须验证 GPU 写入对 CPU 拷贝可见，不能用“完成提交”替代缓存维护
或 fence 完成。现有 IOSurface 分配不自动具备 GPU 映射能力。

## 移植与源码边界

- 不能把 Panthor 和 Panfrost 一并称为 GPL-only。已核对 Linux v6.12
  Panthor 的 drv/fw/mmu/gpu/heap/sched/device/gem 八个 `.c` 文件，
  SPDX 均为 `GPL-2.0 or MIT`；Panthor UAPI 头是 MIT。可按 MIT
  选项评估复用，须保留所需声明并逐个审查其余文件与依赖。
  Linux DRM、调度、内存与锁 API 仍需要移植，许可允许不等于可直接链接。
- 同版 `panfrost_drv.c` 的 SPDX 为 GPL-2.0；所读 MTK kbase 源码
  标记 GPL-2.0（部分带 Linux-syscall-note）。不能由 Panthor 的
  双许可推导这些文件也能按 MIT 引入。
- Mesa 及其依赖同样逐文件核对许可；不要把整个项目简单标成 MIT。
- Arm CSF 与 MTK GPUEB 固件应核对当前设备实际使用的版本和许可；
  固件文件、设备 dump、序列号和 Apple 资源留在 gitignored 目录。
- Android kbase 路线可作命令/固件参考，但 `/dev/mali0`、Linux
  kbase ioctl、bionic 用户态并不会因此出现在 XNU 中。

## 本轮交付与下一步

固件启动和全局握手的代码、镜像构建参数、严格报告解码、MMIO 状态机测试
均已落地；所有硬件证据保存在忽略的 research 目录，摘要和哈希进入版本库。
下一步先锁定 EMI 读取的最小必要条件，再用已成功的2426配置采集每组的
CS 数量、输入/输出页和 suspend-size 等 capability，按 Panthor 的组/队列
握手建立一个有界测试提交。常驻 XNU 驱动需把本轮探针的“测试后复位退出”
改成明确的电源、页表、固件与 BO 生命周期；不能直接把探针当成渲染驱动。
