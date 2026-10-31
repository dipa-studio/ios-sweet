# MT6983 GPUEB 启动交接与只读探针

日期：2026-10-31。用户确认设备可在线测试，并提供完整
`matisse_images_OS2.0.2.0.ULKCNXM_14.0`。用户明确实机 LK 是自行修改版，
后续以实机 dump 为准。本次仅只读采集与本地编译，没有刷机或重启。

## 确定的启动分支

新 Recovery inventory `recovery-live-2`、`recovery-live-3` 均完成。
实机是 matisse、slot `_a`、root Recovery，内核为
`5.10.209-android12-9-00019-g4ea09a298bb4-ab12292661`。
没有 `/dev/mali0`、Mali/GPUEB/gpufreq binding；SCPSYS driver 已绑定。
`CONFIG_DEVMEM` 未启用且 `/dev/mem` 不存在，因此不能靠用户态 devmem 探测。
GPU_ID 和 CSF 运行时 ABI 均未读取。

`/proc/pl_lk` 140879 bytes，SHA256
`937ed759aebada703fae17068dd7503823e9d5592dd4c812a0ed8713e14942da`，
记录 `lk boot mode = 2`、`load gpueb takes 0 ms`。新 live DT 的
`/chosen/atag,boot` 是小端结构，内容为
`<16, 0x41000802, 2, 2>`；不是普通大端 FDT 数字属性。

**零耗时本身不能证明跳过**。实机 LK 代码的独立证据为：

| LK payload 内偏移（不含 0x200 MTK header） | 指令/行为 |
| --- | --- |
| `0xc998..0xc9a8` | 截断 mode 到低 8 位，比较 2；非 2 跳到 `0xca10` |
| `0xc9ac..0xca0c` | mode 2 只输出计时，不调用 ADSP/GPUEB/VCP loader |
| `0xca4c..0xca54` | 其他 mode 调用 `0x1ff4c`（GPUEB loader），保存返回值 |
| `0x1ff88..0x1ffa8` | loader 检查 MFG0 电源位，未置位返回错误 |
| `0x2005c..0x200b8` | 查找 `/soc/gpueb`，注入 BE64 `gpueb_mem_addr/size` |

因此 **Recovery 分支未加载 GPUEB** 是已确认结论；不能从 Recovery
缺少共享内存推断正常启动同样缺少。正常模式是否成功启动 GPUEB、
它分到哪个 PA，仍须在同一次正常 LK 跳转时测量。
不得把 Recovery DT 的静态配置当作固件就绪证据。

## 刷机包与实机比对

| 组件 | 比对结果 |
| --- | --- |
| gpueb.img | 包内 438848 B 与实机两槽前缀完全相同，两槽剩余字节均为零 |
| dtbo.img | 包内 75136 B 与实机 dtbo_a 前缀完全相同，尾部全零 |
| super.img | 与此前松散 super 完整 SHA256 相同，复用已提取 KMD/CSF |
| lk 主 payload | 755704 B；实机与包内仅 59 个字节不同，符合用户修改说明 |
| LK bl2_ext / aee / lk_main_dtb | 分组件逐字节相同；偏移因证书长度变化移动 0x430 |
| vcp.img | 与此前松散文件相同，是 RV55 VCP，不能代替 GPUEB |

实机 LK payload SHA256：
`5310a43ac8b7aec6de3d1571b7012cb6ba3600958db3e4e9df4372fdc642ee84`。
嵌入 DTB 在实机分区 `0x27d310`，包内 `0x27cee0`，均为 335048 B，
SHA256 `783b7fb871087991e97d0d944932981d7b11e207deef2f74d67e8a20cc12ffae`。
整分区按固定偏移比较会把后续位置移动误报成大量代码差异。

新增 `tools/android-mtk.py` 按 MTK v1 扩展头检查范围、对齐和组件名，
逐组件哈希比对。未知 trailer 单独报告，不猜测其中的魔数；证书
只视作数据，**没有执行签名认证**。33 个包内镜像/二进制和 super
均已记录文件大小、magic 和 SHA256；其中 17 个 MTK 容器已完成结构
解析，不表示已完成每个子系统的逆向。

GPUEB 主组件名 `tinysys-gpueb-RV33_A`，payload 从 `0x200` 开始，
长度 `0x6a1af`；后面是 cert1/cert2。实机两槽整分区 SHA256 均为
`0650aa96d8df7cf98b6b63e8ebaeb02d6b323989d769b1b7ab8c4e0884ae489d`。

## 已实现的协议边界

独立编写 `xnu/gpu/mtk_gpueb_protocol.{c,h}`，未复制 GPL 平台实现。
事实来自包内 wrapper ELF 的指令/relocation，并与固定的 MT6983
参考源码核对：`xiaomi-rubens@270b84910b941bf75490fccdb5fb2b3021dd7cbf`。

| 字节偏移 | INIT_SHARED_MEM 命令内容 |
| --- | --- |
| 0 | LE32 command = 0 |
| 4 | LE32 target = 0 |
| 8 | LE64 status PA |
| 16 | LE64 debug PA |
| 24 | LE32 status bytes = 0x400 |
| 28 | LE32 debug bytes |

POWER_CONTROL 是同样 32 B 消息：command 6、target 0、offset 8
为 LE32 power 0/1，其余字节清零。回复的有符号 return value 位于
offset 8；校验 command/target 并向 caller 传播负错误值。
这些是编码/校验函数，**没有 mailbox 传输或电源状态机**。

内存表必须是合法且无重复 ID 的 `(ID, size)` 对；按 ID 顺序计算
各区间，全部落在运行时给出的保留空间中。GPUFREQ 当前表为 4 KiB，
status 占 1 KiB、debug 占剩余 3 KiB。验证 PA 加法、范围、大小，
失败不发布输出。不会使用猜测地址，也不会直接解引用这些 PA。

新 DT 报告按发送表再接收表推导 single-mailbox 布局：
`IPI_ID_GPUFREQ` channel 1，TX byte offset `0x10`，RX `0xbc`，
各 8 words；总计 69/160 words。`MEM_ID_GPUFREQ` ID 0、4 KiB，
`MEM_ID_LOG` ID 1、0x180000 B。配置来自新 live DT；实际 mailbox
控制寄存器/中断顺序仍需独立确认，不能仅凭此开始发送。

## 诊断镜像与测试限制

`tools/mkentryprobe.py --level gpueb` 新增 FDT-only 探针。
它只记录 LK mode、Mali DT 范围、GPUEB runtime memory 和 GPUFREQ
分区描述，然后返回内嵌 Linux；不读取 GPU/GPUEB 寄存器或共享内容，
不发 IPI，不上电，不初始化 UFS。状态 `0x9000` 只表示结构校验
通过；保留区覆盖、固件就绪和电源所有权仍未验证。

实际构建基于包内 boot.img（SHA256 `8775a30a...95d9cb7`），
NDK 28.2 LLVM；镜像 20963328 B，SHA256
`094d4e563a97317119cbcdab0d3f1bda34ae3b49f694e3b95ca7b671b9b7a71f`。
解压长度 48945268 B，小于实测 DTB load limit `0x7c80000`；
ramdisk/signature 与模板逐字节相同；内层 kernel 仅 banner 改动。
旧恢复备份本身已有 2 MiB 历史 entryprobe，故没有把它再次包一层。
旧备份内层 kernel 与包内 kernel 的差异也只在旧 banner。

**此镜像是 build-only，尚未满足正常模式实测条件**：实机 vendor_boot
只有 4 B platform fragment，Recovery 内容放在 type 2 fragment。
正常 LK 启动是否选入该 fragment 未验证；直接正常启动这个包内
boot.img 可能进入不可用的 Android，不能当作可靠日志收集环境。
以 Recovery 启动只能再次看到 mode 2 跳过 GPUEB，无法回答正常交接。
此外，loader 动态分配 2 MiB shared 与 20 MiB 额外区域；正常启动
所得 PA 尚未知，必须检查它们与 XNU RAM window
`0x100000000..0x22e000000` 的重叠，不能仅沿用 Recovery 的静态空洞。
下一步应准备完全在 RAM 中运行、禁止挂载 userdata 的收集 ramdisk，
或为既有 XNU 路径增加同启动交接日志；完成后再请求具体 boot_a 测试
授权。不要运行旧 run-ui 脚本或刷 vendor_boot/LK 来解决这个问题。

验证记录：GPUEB 10 测试、entryprobe 14 测试、Android readers 7 测试、
CSF 1 测试、shim/FDT 8 测试、board 9 测试、keys 4 测试，共 53 PASS。
CSF 与 GPUEB C harness 均运行 ASan/UBSan，各 8192 确定性变异。
新协议单文件 `arm64-apple-darwin -ffreestanding -Wall -Wextra -Werror`
编译通过。完整探针链接通过；没有完整 XNU build、新 CI run 或本次 boot。
原始 dump、固件、日志、反汇编、镜像和 JSON 清单留在忽略的
`research/matisse/20261031-gpu/`，不提交 git。
