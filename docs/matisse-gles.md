# Matisse 用户态 GLES

2026-11-09：当前选择原生 OpenGL ES 路线，复用 HakiOS 的
`EAGLContext → Mesa Gallium → IOSurface` 接口。Matisse 已有的
CoreAnimation 软件 UI（2317）与这里新增的 Mesa GLES 路径是两项不同的结果。

| 路线 | 对本项目的作用 | 当前成本 |
| --- | --- | --- |
| GLES / Mesa Gallium | 直接承接 iOS CoreAnimation 的 EAGL 调用 | HakiOS 已有桥接代码；需验证 20H392 ABI，接入 G710 CSF 后端 |
| PanVK | Vulkan 驱动，适合后续 Vulkan 应用和 API 转换层 | 仍需同一套 G710 内存、CSF 队列、同步基础；不直接提供 EAGL |
| GLES / Zink / PanVK | 用 Vulkan 实现 GLES | 比当前原生 GLES 多一层需要适配、验证的接口，暂不作为第一条路线 |
| Metal / AIR→NIR | 承接 Metal 和更完整的 CoreAnimation 渲染功能 | 还需 AIR 编译器、Metal 对象与命令生命周期；参考项目记录过异步错帧 |

上述选择依据移植工作量和已有接口，不代表对 G710 性能的实测比较。
不能把 G52 的运行记录或 G610 的支持情况当作 G710 已成功。

参考固定在：

- [hakios-mt6768](https://github.com/oosexgang/hakios-mt6768/tree/84b025233e7350f3549ec5b8eb330fd74b4602f4)。
- [公共树 mtk](https://github.com/oosexgang/hakios-xnu-kernel/tree/620c77507a17ad23ac5a40bad900abe9ed4d7740)：实际用户态在 `userland/src/eagl.c`、`gl_osmesa.c`、`tools/mesa/`。
- Mesa 25.0.7，归档 SHA256 `592272df3cf01e85e7db300c449df5061092574d099da275d19e97ef0510f8a6`。

设备仓库的 README 提到用户态未合入；当前公共树 `mtk` 已包含它。
公共树的 `panfrost-darwin.patch` 硬编码只编译 v7，`RedwoodMali`
使用 JM job chain。MT6983/G710 是 v10/CSF，不能直接套用这部分。
首个构建仅应用 OSMesa ES profile 补丁，显式使用 softpipe，未声称 GPU 加速。

构建命令（路径换成本机 SDK、编译器和固定的参考树）：

```sh
python3 tools/build-sweet-gles.py \
  --work research/matisse/20261109-hakios \
  --reference research/matisse/20261109-hakios/common \
  --sdk /path/to/iPhoneOS.sdk \
  --cc /path/to/XcodeDefault.xctoolchain/usr/bin/clang
```

Python 环境需要 meson、mako、packaging；PATH 中需要 ninja 和 bison >= 2.7。
结果与哈希写入工作目录 `out/manifest.json`。第三方源代码、SDK 和编译产物不进 git。

`userland/gles-probe.c` 执行两份 GLSL ES 着色器，绘制四帧，检查背景、
三角形、透明混合共八个采样像素。256×256 的回读结果转换为顶向下 BGRA，
写入独立 IOSurface，再用现有 AppleCLCD SwapBegin/SwapEnd 提交到原生画布。
这里的放大与显示复制由 CPU 完成。探针还创建 EAGL API 3 上下文，通过
HakiOS 宏函数表清屏并检查第九个像素；记录本机 Apple GL 入口用于 ABI 核对。

首轮试验 2427 复用已验证的 2316 内核，以 `launchdsuffix=gles-probe`
选择 `/usr/appleinternal/sbin/launchd.gles-probe`。iOS 文件系统只读挂载，
原有分区尾部的持久日志仍可写。安装使用完整根镜像副本、原生 HFS 日志重放、
离线 fsck 和逐块前像/回读核对；不改变 GPT。

2427 实机通过：`softpipe / OpenGL ES 3.1 Mesa 25.0.7`，九项像素检查全部
成功，四帧 IOSurface 提交，EAGL API 3 宏表读回 `64,128,191,255`，GL 错误为零。
用户确认屏幕出现蓝底红色/绿色三角形。内核另保存了前三帧的 framebuffer
缩略图。256×256 绘制加回读分别为 13.766、7.590、10.345、7.527 ms；
这不是 1440×3200 界面性能，也不是 GPU 加速。Fastboot 在125.91秒被观察到，
完整 boot_a 已恢复并验证 SHA256 `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`。
原始证据位于忽略的 `research/matisse/20261109-hakios/`。
GPU 固件启动和全局握手的已验证结果见 `matisse-gpu-20261109.md`；
仍需常驻 XNU 驱动、BO/VM、CSG/CS、tiler heap、完成同步和 IOSurface 导入，
才能把这里的软件 GLES 后端换成 G710 硬件后端。

## 2428：界面可见，但尚未启用 EAGL 桥接

2428 复用 2316 内核，用户观察到锁屏或主屏幕。持久日志确认
backboardd 和 SpringBoard 各启动一次，未记录 backboardd 崩溃，
但 `SWEET GLES:` 和 `redwood-gl:` 均为零次。因此不能将这次 UI
归为新 Mesa 后端的成功。169.12 秒观察到 Fastboot，随后完整
boot_a 恢复并独立核对上述 SHA256；本地 `result2428.json` 保存了结果。

静态核对找到了注入链路的两个缺口：

1. HakiOS 的 `xnu/redwood.patch` 在 `exec_extract_strings()` 内追加
   `DYLD_INSERT_LIBRARIES`，并说明 launchd 会过滤任务字典中的
   `DYLD_` 变量。单独修改 launchd plist 不是它使用的注入方式。
2. 20H392 的 `/usr/lib/dyld` 在 `0x5cc0c` 的
   `amfi_check_dyld_policy_self` 调用 `__mac_syscall("AMFI", 90, arg)`；
   `arg` 是 `{ uint64_t input_flags; user_addr_t output_flags; }`。
   失败时 `SyscallDelegate::amfiFlags` 返回零，路径环境变量不被处理。
   原 SWEET AMFI 策略名为 `SWEET AMFI`，且没有 syscall callback。
   HakiOS 的 `xnu/files/bsd/kern/kern_minimac.c` 实现了这个 ABI。

0205 补丁添加固定的 loader 环境变量及 AMFI 90 号接口，二者都只在
`sweetgles=1` 且目标为 64 位 backboardd 时启用。AMFI 输出 `0x12`
只启用路径和诊断环境变量，不放开自定义共享缓存、插入失败忽略或
interposing。已有相同环境变量不重复添加，不同值返回 EINVAL。
内核分别记录 exec 注入与 AMFI 握手，方便区分后续加载/渲染问题。

宿主 ASan/UBSan 测试执行补丁中的实际函数，覆盖启用范围、重复/冲突
环境变量、参数空间不足，以及 AMFI 的两级指针复制与 EFAULT 传播。
2429 是验证这项内核修复的试验编号；上机结果需要另行记录。

2429 没有形成有效内核试验：用户只看到 REDMI，回收的尾部日志和
marks 都与 2428 相同，不能解释为新内核已经进入 launchd。新 payload
比旧版本大 896 字节，而复用的 shim 内含旧的 `EMBEDDED_XNU_BYTES`；
loader 的长度检查在跳转 XNU 前拒绝了它。完整 boot_a 已恢复核验。

`tools/repack-sweet-ui.py` 修正此打包流程：使用冻结的已验证 shim
源代码/对象，先重编旧 loader 并逐字节复现整个基准 Image，再按新
payload 大小重编 loader。保留原 ramdisk、签名和 Android header 参数。
2430 的基准复现通过，使用同一个 2429 内核（mark 2429），只修正
loader 和 trial 参数。每次必须先验证日志新鲜度与 trial 身份，再
解读用户态输出。原始 2429 运行脚本不可重复执行。

## 2430：注入成功，定位 IOSurface 接口缺口

2430 的 console 内容与前像不同，boot-args 为2430，marks 为新内核2429；
270850字节、flush111，完整 boot_a 已恢复并独立核对。用户看到持续跑码。
8次 backboardd 启动均加载桥接，8/8 EAGL 方法替换成功，7次创建
softpipe ES3.1上下文；没有已完成的 GLES 显示帧。

首个1440×3200目标为 `b3a8` 双平面表面，HakiOS 的 GLES 桥接只接受
BGRA或无格式的单平面目标，因而拒绝 attach，首个 draw 返回0x506。
随后 selector6 被 SWEET 的默认分支以全零结果宣告成功，伪造出没有
共享状态页的 IOSurfaceClient；崩溃位于 `IOSurfaceClientGetBulkAttachments`
复制 `shared + 0x30`，FAR为0x30。参考树的 MiniIOSurface 对6/7明确
返回 Unsupported，并在新建表面时将 b3a8 协商为 BGRA，且支持
`IOSurfaceAddress` 包装调用方内存。这些接口需要一起移植，不能将
原有双平面像素直接按BGRA解读。

`tools/sweet-gles-evidence.py` 从原始环形日志验证内容新鲜度、trial和
内核编号，分别报告库加载、上下文和带 display surface 的绘制帧。
七项回归检查通过；旧2429捕获被正确拒绝。工具不会把软件帧或库
加载标为硬件加速，也不自动断言屏幕视觉质量。

## 2431：系统 GLES 绘制已验证，交互延迟待定位

0206 修复目标格式协商与 IOSurface 调用方内存处理后，2431 的新鲜日志
确认一个 backboardd 实例加载桥接并建立 softpipe ES3.1 上下文。37条
帧记录中26条包含已知 IOSurface 目标绘制，未记录着色器编译、程序链接、
GL 调用错误或 backboardd 崩溃。用户看到正常锁屏和跳动的时间，但滑动
没有刷新、按键没有可见响应。这里已实现系统软件 GLES 渲染，尚未实现
G710 硬件加速，也不能将锁屏可见解释为交互已经正常。

日志包含55条触摸、26条按键记录以及显示关闭/开启请求。帧记录的中位
耗时178.745ms、最大19.365239s；该值包括首个绘制至帧结束之间的所有
时间，不能直接当作 GL 执行时间。长帧的显示复制仅数毫秒。下一轮使用
桥接已有的 `glslow` 诊断区分慢 GL 调用与调用之间的等待。触摸日志里的
1080×2400是驱动归一化坐标，0111补丁已按实际面板与逻辑画布转换。

2431在201.15秒观察到 Fastboot，完整 boot_a 恢复并再次独立核对
SHA256 `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`。
源码提交7591fa4，本地内核构建成功；GitHub Actions dispatch 被禁用，
没有新的 CI run。原始日志及结果保存在忽略的
`research/matisse/20261109-gles-inject/`。
