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
