# matisse / MT6983 GPU CSF bring-up — 状态总览（2026-11-06 22:50，按用户要求暂停）

本文是这一阶段工作的**唯一总入口**。逐次试验的完整证据在
`docs/matisse-gpu-mcu-wall.md`（36 节，按时间顺序），当日记账在
`.workbuddy/memory/2026-11-06.md`，活跃笔记在 `NOTES.md`。

---

## 1. 现在停在哪

- **设备安全**：Redmi K50 Pro（matisse / MT6983）处于 **recovery**，
  `boot_a` 为原始基线 `2931647a…86b1`，读回校验一致。**没有半成品写入。**
- **代码全部入库**，最后一个提交 `d0a5da7`。
- **2391 只准备了一半**：内核已建（`8df00489…562011`，16,724,248 B，
  `SWEET_BUILD_ID 0x2391`）、builder 规格、报告判读、测试都已写好；
  **镜像未构建、runner 未生成、未上机**。
- 测试：**262 通过 / 3 跳过**。

---

## 2. 目标与基线

| 项 | 值 |
|---|---|
| 目标 | 让 XNU/iOS 16 在 MT6983 上驱动 Mali-G710（CSF/Valhall），完成 MCU 初始化与上电 |
| 厂商驱动版本 | `mali-r32p1`（与参考仓库一致） |
| 参考源码 | `MiCode/Xiaomi_Kernel_OpenSource`，分支 `rubens-s-oss`（Redmi K50，MTK tag `t-alps-release-s0.mp1.tc8sp2-mt6983-V1.0.1`） |
| CSF 固件 | `mali_csffw.bin`，258,048 B，sha256 `de22d2fc…9a`；**与 `_reload.bin` 逐字节相同** |
| 固件布局 | VA0 向量表（SP `0x02040000`，reset `0x010018ed`），代码段 `0x01000000`+64 KB，另有 `0x02000000`/`0x02800000`/`0x04000000` 数据段 |
| 试验基线分区 | `boot_a` = `2931647a56039722ea2585990b8ef3b1a2daf4c9b990231879f753049eaf86b1`（64 MiB） |
| 内核产物（**正确路径**） | `xnu/out/local/build/xnu.obj/DEVELOPMENT_ARM64_SWEET/kernel.development.sweet`（16,724,248 B） |
| 内核构建 | `DEVELOPER_DIR=/Users/xiaohuasheng/Downloads/Xcode.app/Contents/Developer tools/build-xnu-local.sh xnu/out/local` |

---

## 3. 已确立的事实（都有硬件证据）

1. **MCU 启动序列正确**：`MCU_CONTROL = MCU_CNTRL_AUTO(2)`，随后等全局中断。
   2372 实测 + 参考仓库 `kbase_csf_firmware_enable_mcu()` 源码双重确认。
2. **AS_MEMATTR 与厂商一致**：cached→索引 0，其余→索引 5，仅 `SHARE_BOTH` 带 SH；
   厂商值 `0x00084C8D888D8F88`。2380 实测回读 + `convert_mem_flags()` 源码确认。
3. **页表是对的**：2388 从 shim 实际交给 AS 的 arena 里读出 live leaf，
   `0x01000000→0x401a4000`、`0x01001000→0x401a5000`、`0x0100E000→0x401b2000`、
   `0x0100F000→0x401b3000`，同一张 L3 表四个相邻条目，flags 全为 `0xc47`。
   **没有过期条目、没有影子映射、没有第二张表。**
4. **未映射读的拒绝到达 MMU、不到达 MCU**：2384 故意读 `0x03000000`，
   得到 `AS_FAULT = 0x7cd002c2`、`AS_FAULT_LO = 0x03000000`，与 2375 读未映射堆时逐字节相同。
   **AS 拒绝在 MCU 侧表现为「事务永不完成」，不是会触发异常的总线错误。**
5. **reset 向量（VA 0x4）确实被使用**：2385 指向 `0x0100E001`、2389 指向 `0x01001001`，
   两处程序都被执行并写出标记。
6. **厂商入口 `0x010018ec` 可达**：2390 **向量字一个字节没动**，
   核写出了 `0x010018ec`。即**厂商固件在这里确实起步**，`version = 0` /
   `firmware_ready = 0` 表示「起步后挂住」，不表示「从未启动」。
7. **`0x01000200` / `0x01000600` / `0x01001200` 三个地址从未执行过**：
   无论是 reset 取指（2386/2387/2388）还是运行中 `bl` / 数据读（2373/2379/2382/2383），
   全部挂住、无异常。这三轮的 `cleanup_error = -53`，而成功的三轮为 `0`
   ——证明是真实的未启动，不是证据过期。

---

## 4. 已被推翻的判断（避免重犯）

| 曾写下的结论 | 被谁推翻 |
|---|---|
| 「只有已驻留的块能用」 | 2385：`0xE000` 冷块在 reset 首周期跑通 |
| 「墙是运行中核的取指通路」 | 2386：`0x200` 连 reset 取指也不行 |
| 「坏的是 `0x200` 这一块」 | 2387：同页 `0x600` 同样不行 |
| 「整页 0 都不可达」 | 2389：页首 `0x1000` 能跑 |
| 「只有页首能起步，低 12 位被丢弃」 | **2390：`0x18ec` 非页首、非 512 对齐，照样跑通** |
| 「2375 的 `-54` 是核进了异常」 | 2384：`-54` 是 shim 读到 `mmu_raw`/`AS_FAULT`，核是挂住的 |
| Python 页表复刻的 leaf 值 | 用真实 `mali_csf_memory.c` 编译的 host 程序读出 `…c47`；**复刻不具权威性，不得再引用** |

---

## 5. 还没回答的问题（按价值排序）

**A. 为什么 `0x200` / `0x600` / `0x1200` 不执行？**
六轮镜像与厂商原版逐字节比对，所有差异都在预期区间，排除构建污染。
`0x1000`、`0xE000`、`0x18ec` 能跑，`0x200`、`0x600`、`0x1200` 不能跑。
这是目前唯一没有解释的硬件行为。

**B. 向量是「按字面执行」还是「非页首时回退厂商入口」？**
2390 的标记在 `0x18ec`，两种读法都解释得通。**2391 就是为此准备的**：
向量 → `0x01001A01`，同时在三个落点各放一份程序
（`0x1A00` 字面 / `0x1000` 页首 / `0x18EC` 厂商入口），标记本身说出答案。

**C. 厂商 handler 从 `0x010018ec` 起步后挂在哪里？**
这是真正的目标：既然入口可达，剩下的就是找到它卡住的那条取指/访存。
下一步仪器应是**沿厂商代码路径布点**，而不是继续搬向量。

**D. 为什么固件永远不 ready？**
大概率是 C 的直接后果，但尚未实测。

---

## 6. 工程链路（怎么用）

```
改代码 → 内核 bump SWEET_BUILD_ID → build-xnu-local.sh
      → tools/matisse-shim-gpu-image.py --build-id 0x23xx … → 镜像 + manifest
      → research/.../shimXXXX-…-run-once.py preflight（只读）
      → 写 boot_a 前再次人工确认 → gpu-normal（写→启动→采证据→恢复→校验）
      → tools/matisse-gpu-report.py after-marks.bin --build 0x23xx 解码
```

关键约束：

- **必须 bump `SWEET_BUILD_ID`**（`xnu/out/local/xnu/bsd/dev/sweet_ufs.c`）。
  2385 忘了，marks 带的是上一轮编号；报告用 `--mark 0x23xx` 指定实际标记即可解码。
- **raw 传输**：`tools/fbraw.py` 依赖 `pyusb`（已装 1.3.1）+ libusb。
  **fastboot CLI 在这个 LK 上会卡死**（`could not clear input pipe; e0005000`），不要走它。
- **恢复卡住先采证据**：`restore-only` 会在完整写回**之前**抓 `after` marks；
  恢复进 recovery 的是 stock 内核（不写 marks），证据不会被覆盖。
- **构建器拒绝覆盖已有输出目录**：有缺陷的产物归档为 `…-noleaf` 之类并写 NOTE.txt。
- leaf 属性与 shim 宏共用 `LEAF_PROBE_BUILDS`（0x2388–0x2391），有测试防止再次漂移。

---

## 7. 本阶段修掉的工程缺陷

1. `pyusb` 缺失 → raw 通道退回 fastboot CLI → 恢复卡死、`boot_a` 半写。
   装 `pyusb 1.3.1` 后，`fbraw reboot-recovery` + `restore-only` 闭环（2387、2389 各用一次）。
2. 取错内核产物（`xnu/out/local/kernel.development.sweet`，10-25 旧文件）→ 用户报告「卡 REDMI」。
   正确路径见第 2 节，两次废产物已归档。
3. `SWEET_BUILD_ID` 未 bump → 新增报告 `--mark` 参数。
4. leaf 门控两次漂移 → 统一 `LEAF_PROBE_BUILDS` + 回归测试；2389 的捕获用 `--allow-missing-leaf` 解码。
5. runner 恢复等待无上限 → 2387 起 300 s 超时即报错退出。
6. Python 字符串里的撇号导致 runner 语法错误（两次）→ 授权文本不再用缩写撇号。

---

## 8. 如何继续（恢复点）

1. 构建 2391 镜像：与 2390 同参数，`--build-id 0x2391`，
   `--kernel-shasum 8df00489464cd5016ba46a63e2c743c6774b51a6d30f96f6e5c01beb2a562011`，
   输出目录 `research/matisse/20261031-gpu/shim2391-entryrule-ready`，
   `--trace-probe --ro-as-rw --relocate-code --mcu-control 2`。
2. 校验 manifest：`reset_vector` 应为 `was 0x10018ed → now 0x1001a01`，
   `cold_boot.landings` 三项，`leaf_probe` 存在；ADT 里 `sweet-csf-leaf` 32 B。
3. 生成 runner（复制 2390 的，换镜像名/sha/build id），跑 `preflight`，
   再按 AGENTS.md 要求确认后 `gpu-normal` 一次。
4. 若 B 有了答案，转向问题 C：沿厂商 handler 布点。

---

## 9. 一句话结论

**初始化与上电序列已经和厂商源码对齐、页表已被实测证明正确、MCU 确实在跑；
墙不在翻译、不在内存通路，而在「某些地址取不到指令」——
具体是 `0x200` / `0x600` / `0x1200` 这三个点，以及厂商 handler 起步之后的那一步。**
