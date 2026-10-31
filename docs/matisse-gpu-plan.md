# matisse GPU 路线与证据边界

日期：2026-10-31。目标板是 Redmi K50 Pro / matisse / MT6983，
不是 sweet / SM7150，也不是 UniXNU 的 SM8550。

## 当前基线

- 本项目的 0x2317 实机已验证原生 1440×3200、触摸和三个实体键。
  显示仍走现有 IOSurface / AppleCLCD / framebuffer 路径；这不是 GPU 验证。
- 此轮之前的完整 stock boot_a 恢复已校验；没有正在运行的硬件试验。
  设备状态以 NOTES.md 的 ACTIVE 交接为准。
- 本地厂商参考源码 `research/matisse/mt6983.dts` 的
  `mali@13000000` 声明 `mediatek,mali` / `arm,mali-valhall`，
  MMIO 范围 `0x13000000 + 0x480000`。它是源码事实，
  不等于已核对当前 Recovery 的 live DT 或读取 GPU_ID。
- 同一参考 DTS 声明 GPUEB 和 `gpufreq_wrapper`，两处
  `gpueb-support = <1>`。不得假定这台机器没有 GPUEB。
- 本地 `MiCode/MTK_kernel_modules` 的 `rubens-s-oss` 提交
  `c66b3c9ce7b5c0bc3d72a829f6542200deaa8a9c`，其
  `gpu/gpu_mali/mali_valhall/mali-r32p1/drivers/gpu/arm/midgard/Makefile`
  在 MT6983 的 OOT 配置中明确启用 `CONFIG_MALI_CSF_SUPPORT := y`。
  CSF 固件加载源码的默认名为 `mali_csffw.bin`。这是邻近厂商源码
  的支持证据，不等于已经确认本机正在加载 r32p1 或该固件。

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

预期硬件为 Mali-G710（CSF），因此以 Panthor / PanVK 的 CSF 路径
作为调查方向；最终必须用本机驱动配置、GPU_ID 和固件 ABI 确认。
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

本轮先固定路线和证据要求，不声称已经实现 GPU、Metal 或 Vulkan。
下一项是阶段 0 的只读基线与阶段 1 的接口审计。任何 boot_a、
userdata 或固件持久写入都仍需当次确认；不修改 GPT。
不要复用或导入历史 run-ui 试验脚本。

## 可核对的来源

- [Mesa 官方 Panfrost / PanVK 支持表](https://docs.mesa3d.org/drivers/panfrost.html)。
  本轮抓取的原始 HTML SHA256：
  `f1d24d83909a710631a3f3a57c1676cf3d1d86e189f5776cdb699014c932a36a`。
- [Linux v6.12 Panthor 驱动](https://github.com/torvalds/linux/tree/v6.12/drivers/gpu/drm/panthor)
  与 [Panthor UAPI](https://github.com/torvalds/linux/blob/v6.12/include/uapi/drm/panthor_drm.h)。
  `panthor_drv.c` SHA256：
  `a330beefa792fbf15d3772ea30f47ee530095a95d65851eb646bd65d739599f3`；
  `panthor_drm.h` SHA256：
  `49ef00061b27b4e3b889347a31cb4481e96900c648c9020f25decbbe9be9bf52`。
- [MiCode MTK 模块参考提交](https://github.com/MiCode/MTK_kernel_modules/tree/c66b3c9ce7b5c0bc3d72a829f6542200deaa8a9c)。
- [AdrenoMetal 说明](https://github.com/UniXNU/AdrenoMetal)：本轮读取的
  README 确认 metal2vulkan + Turnip 和 sheng/A740 GPU composition，
  不据此宣称其 AIR 前端已适配本项目 iOS 16 ABI。

第三方参考文件及逐文件 hash 清单保存在忽略目录
`research/matisse/20261031-gpu/`；未将第三方源码或固件加入 git。
本轮未能读取 UniXNU 的 GPU 移植网页（HTTP 403），不把该页视作
已独立核实的实施细节。
