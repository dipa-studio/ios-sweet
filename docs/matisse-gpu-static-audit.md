# MT6983 GPU 静态审计：本地镜像与第一段实现

日期：2026-10-31。用户确认 Android 因 userdata 改动不能正常启动，
后续仅做静态分析。本轮没有启动 Android、加载 GPU 模块、访问 GPU
MMIO、刷分区或修改 userdata。GPU 加速尚未实现。

## 输入与来源边界

使用 `/Users/xiaohuasheng/Documents/` 下的 `super.img`、`lk.img`、
`vcp.img`、`dtbo.img`。镜像及所有提取物均未加入 git。super 中的
build.prop 标记 `OS2.0.2.0.ULKCNXM`，构建日期 2025-04-01。
镜像中的配置不等于当前 Recovery 驱动或实际 GPU_ID 读数。

转为静态分析前，ADB 曾确认设备为 matisse、slot `_a`、root Recovery，
内核 `5.10.209-android12-9-00019-g4ea09a298bb4-ab12292661`；当时
没有 Mali/GPUEB/gpufreq 模块、`/dev/mali0` 或 Mali driver binding，
runtime_status 为 `unsupported`。随后设备断开，自动采集未成功，
不能声称已取得本轮新 live.dtb 或 GPU_ID。已有 2026-10-26 Recovery
DTB 仅作为历史静态输入，报告单独注明来源。

`tools/android-super.py` 直接读取 sparse super，验证 LP geometry、
header、tables 的 SHA256，再只提取指定分区；不展开整个 8.5 GiB
逻辑 super。DONT_CARE 按零读取，仅用于静态文件视图，不用于刷机。
未校验 sparse 可选 CRC；LP 校验不能替代整个镜像的签名验证。
提取出的 vendor/vendor_dlkm 为 EROFS，使用 erofs-utils 1.9.4 的
`dump.erofs --cat` 读取指定文件，无挂载或文件系统修复。

| 提取分区 | 字节数 | SHA256 |
| --- | --- | --- |
| vendor_a | 2041831424 | `cc8a64dca53b410afd7c3d2bcd01d66af0c1d5d0be2073231bcbd61219defe59` |
| vendor_dlkm_a | 19492864 | `b70368db18e31a7f720be1c2ce592560786326a792a4c4103ec68547c7d4514b` |

源 sparse super 为 7918405960 bytes，SHA256
`289951fb8db34509591ada6259737b0522cc5a923f878171e9b746031e601957`；
哈希前后文件大小和 mtime 一致。

## 已确认的驱动与固件

| 文件 | 字节数 | 事实 |
| --- | --- | --- |
| mali_kbase_mt6983.ko | 1823016 | `.modinfo`：`r32p1-01eac0 (UK version 1.18)`；含 CSF 路径 |
| gpueb.ko | 111736 | 依赖 mtk-mbox、mtk_tinysys_ipi、mtk-ssc |
| mtk_gpufreq_wrapper.ko | 156096 | 依赖 GPUEB；含 IPI_POWER_CONTROL 分支 |
| mtk_gpufreq_mt6983.ko | 268088 | 同时保留 AP 电源实现；不能据此选 AP 模式 |
| mali_csffw.bin | 258048 | SHA256 `de22d2fc06bc8a859968499a6e609c27fe838be062bf5c97d92ea9f904f7229a` |
| mali_csffw_reload.bin | 258048 | 与上项逐字节相同 |

KMD SHA256 为
`22b26f30a151e9d6791f959cc1f93d1e3f4d4c564537970dadefb0ec2d742a3b`。
模块 vermagic 为 `5.10.209-android12-9-gad068458f122 ... aarch64`，
与刚才的 Recovery 内核标识不同；没有尝试把模块装入 Recovery。

modules.load 的相关顺序为 GPUEB → gpufreq wrapper → MT6983 gpufreq
→ Mali KMD（中间还有其他模块）。完整依赖保存在提取清单。
这些 ELF 用于静态对照；不会作为 XNU 可加载模块。

## CSF 容器解析与内存约束

实际固件符合 magic `0xc3f13a6e`，文件格式 0.1，format hash
`0x01010000`，条目表结束偏移 `0x300`。共有 21 个条目、10 个
内存 section，其中 3 个 protected section。BUILD_INFO 中的 git SHA
为 `99baa9f25d7a4d03cbb9e85f0400f6307d90d58d`。

文件格式与 format hash **不是运行中的 CSF 全局接口 ABI**。
后者需要固件启动后的 GLB_VERSION/capabilities；本轮没有测到。
Panthor v6.12 同名固件容器的解析结构可作参考，但容器能解析不能
证明固件已在 Panthor、XNU 或当前 GPU revision 上运行。

| Section 类别 | GPU/MCU VA | 要点 |
| --- | --- | --- |
| config | `0x00000000..0x00001000` | 4 KiB；无法按 16 KiB VA 粒度直接表示 |
| executable | `0x01000000..0x01010000` | 按 section 权限建立映射 |
| data / zero sections | `0x02000000..0x02040000` | 包含 `0x0203e000`、`0x0203f000` 边界 |
| read-only alias | `0x02800000..0x02840000` | 与数据 section 指向部分相同文件数据；不等同于物理页共享已实现 |
| protected sections | `0x03000000..0x03040000` | 初期不建立 protected GPU 功能；解析器只报告，不装载 |
| shared interface | `0x04000000..0x04094000` | 606208 bytes；带 shared/zero/cache 属性 |

7 个 section 至少一个边界未按 16 KiB 对齐，其中 4 个非 protected。
因此 XNU 的 CPU 16 KiB 页与 GPU/MCU 页表粒度必须分开：可评估从
16 KiB backing page 拆出 4 KiB GPU 映射，但先要确认 GPU MMU
支持位、物理连续性、权限及缓存维护。不能通过把 firmware VA 四舍五入
到 16 KiB 来绕过，也不能把相邻 section 不同权限合并掉。

第一段实现位于 `xnu/gpu/mali_csf_firmware.{c,h}`，是可供后端使用的
无分配 C 解析器：完整验证通过后才调用 section 回调；检查长度、
条目步长、文件范围、VA 对齐、section 重叠、共享区和可选未知条目。
回调接收 caller-owned blob 的有界名称与 section 描述，错误显式返回。
它目前没有加入内核补丁/启动路径，也不会装载或执行固件。

## GPUEB 电源控制与 LK

从 `lk.img` 偏移 `0x27cee0` 提取出一个有效 FDT（335048 bytes）。
GPUEB 节点、双 buck、IPI 表、gpufreq MMIO 与历史 Recovery DT
可相互核对。DTBO 包含一个 overlay；已解析 `__fixups__`，未发现
直接以 mali/gpu/mfg/gpueb 命名的 fixup，不能把它当作 GPU_ID 来源。

LK 包含 `app_load_gpueb`、`tinysys-gpueb-RV33_A`、
`gpueb_mem_addr` / `gpueb_mem_size` 和 GPUEB boot timeout 字符串。
这些证明存在 GPUEB 加载路径；**字符串本身不证明某次启动执行了它**。
`vcp.img` 的头部标记为 `tinysys-vcp-RV55_A`；它不应替代独立
GPUEB 分区镜像。当前输入中尚未找到独立 gpueb.img。

对照厂商源码和带 relocation 的模块反汇编，GPUEB 模式下：

1. 按 `IPI_ID_GPUFREQ` 获取通道；从 LK 提供的信息定位
   `MEM_ID_GPUFREQ`，分配 status/debug 视图。
2. 发送 `CMD_INIT_SHARED_MEM = 0` 注册共享内存。
3. `gpufreq_power_control` 发送 `CMD_POWER_CONTROL = 6`，
   不是直接跳进 AP 的 SCPSYS/MFG 上电序列。
4. 实际 wrapper 二进制调用 `mtk_ipi_send_compl`，消息长度参数为
   8 words、timeout 参数 `0x2710`。这些数值不是可直接发送的完整协议，
   还缺 mailbox 布局、握手、共享状态结构与版本一致性验证。

参考 MT6983 gpufreq probe 在 `g_gpueb_support` 分支跳过大部分 AP
初始化。禁止同时让 GPUEB 和 XNU 各自操作 regulator/PLL/MFG。
历史 Recovery DT 的 GPUEB 节点缺少 `gpueb_mem_addr/size`，
需要查清 LK 的 boot-mode 分支和 shim 接收/保留 live FDT 的方式；
不能用镜像里的静态 DTS 发明运行时保留内存地址。

## Mesa 固定版本审计

已从 Mesa 官方 Git 远端固定 `mesa-25.1.0` 为
`5c142e46f3f6e752ed745fd48912ebb8fad67145`，用于可复现接口分析。
这不是“当前最新版”的声明。其 `pan_props.c` 型号表列出 G610
`0xa867`，没有 G710 条目；PanVK 对未识别型号返回
`VK_ERROR_INCOMPATIBLE_DRIVER`。不能伪装为 G610 来掩盖型号差异。
下一步需对 G710 型号/勘误与合适 Mesa 版本做专项适配。

## 验证与下一步

- 5 个测试用例全部通过：sparse raw/fill/hole 的跨边界读取、LP
  checksum 和恶意 extent、FDT/DTBO 边界、实际 CSF C 解析器。
- C 解析器在 ASan+UBSan 下通过 8192 次固定输入变异；真实
  258048-byte 固件成功解析为 21 条目/10 section。
- `clang -target arm64-apple-darwin -ffreestanding -Wall -Wextra -Werror`
  编译通过。这是单文件交叉编译，不是完整 XNU 构建或启动成功。
- 没有新 CI run、GPU 启动、fence 或显示加速实测；原 0x2317
  UI/触摸/按键证据仍是上一轮硬件基线。

下一项静态工作是 GPUEB 固件/共享内存交接与 mailbox 协议：
先补齐独立 GPUEB 镜像和 LK 分支证据，再实现有界传输后端。
并行的代码依赖是 4 KiB GPU 页表/BO 与 CPU 16 KiB backing 管理，
不能在缺少电源与固件握手时冒进提交队列。

所有原始文件、提取清单、ELF 元数据、反汇编、固件 section map、
Mesa 参考和失败采集清单位于忽略目录
`research/matisse/20261031-gpu/`。不把缺失的 live 读数补成推测值。
