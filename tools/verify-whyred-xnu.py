#!/usr/bin/env python3
"""Reject an XNU source tree that lacks whyred framebuffer and UARTDM diagnostics."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--expected-upstream-commit")
    args = parser.parse_args()
    root = args.source.resolve()
    patterns = {
        "osfmk/arm64/start.s": [
            r"MOV64\s+x0,\s*\(0x9d400000\s*\+\s*2128\s*\*\s*4320\)",
            r"MOV64\s+x10,\s*0x9c000000",
            r"MOV64\s+x9,\s*0x0c170000",
            r"\.macro WHYRED_UART_TX",
            r"WHYRED_UART_WORD 0x30554e58",
            r"WHYRED_UART_WORD 0x31554e58",
            r"WHYRED_UART_WORD 0x32554e58",
            r"WHYRED_UART_WORD 0x33554e58",
            r"WHYRED_UART_WORD 0x34554e58",
            r"WHYRED_UART_WORD 0x35554e58",
            r"WHYRED_UART_WORD 0x36554e58",
            r"MOV64\s+x10,\s*0x0c000000",
            r"ARM_TTE_BLOCK_ATTRINDX\(CACHE_ATTRINDX_DISABLE\)",
            r"Lwhyred_boot_exception:",
            r"mrs x14, ESR_EL1",
            r"mrs x14, ELR_EL1",
            r"mrs x14, FAR_EL1",
        ],
        "osfmk/arm64/sweet_early.c": [
            r"early_fb\s*=\s*\(volatile uint32_t \*\)\(uintptr_t\)0x9d400000;",
            r"#define EARLY_WIDTH 1080u",
            r"#define EARLY_HEIGHT 2160u",
            r"#define EARLY_STRIDE \(4320u / 4\)",
            r"XNU_C",
            r"whyred_boot_uart_disabled = 1;",
            r"XNU_EARLY_PANIC",
            r"sweet_early_hex64\(const char \*label, uint64_t value\)",
            r"XNU_HEX ",
        ],
        "osfmk/arm64/arm_vm_init.c": [
            r"sweet_early_relocate\(SWEET_EARLY_FB_VA \+ 0x01400000\);",
        ],
        "osfmk/arm/arm_init.c": [
            r'sweet_early_mark\(10, "arm_setup_pre_sign done"\);',
            r'sweet_early_mark\(11, "arm_slide_rebase_and_sign_image done"\);',
            r'sweet_early_mark\(12, "boot_args copied"\);',
            r'sweet_early_mark\(13, "cpu_data_init done"\);',
            r'sweet_early_mark\(14, "before PE_init_platform"\);',
        ],
        "pexpert/arm/pe_init.c": [
            r'#include <arm64/sweet_early\.h>',
            r'sweet_early_mark\(17, "PE before SecureDTInit"\);',
            r'sweet_early_mark\(18, "PE SecureDTInit done"\);',
            r'sweet_early_mark\(19, "PE identify machine done"\);',
            r'sweet_early_mark\(20, "PE init debug done"\);',
        ],
        "pexpert/arm/pe_serial.c": [
            r"#define WHYRED_UARTDM_PA\s+0x0c170000ULL",
            r"ml_io_map\(WHYRED_UARTDM_PA, WHYRED_UARTDM_SIZE\)",
            r"\[whyred-XNU\] UARTDM console ready",
            r"whyred_uartdm_read\(WHYRED_UARTDM_ISR\) & \(1u << 7\)",
        ],
        "pexpert/arm/pe_identify_machine.c": [
            r"#include <arm64/sweet_early.h>",
            r"sweet_early_mark\(21, \"pe_identify_machine entered\"\);",
            r"sweet_early_mark\(22, \"PE before SoC base lookup\"\);",
            r"sweet_early_mark\(23, \"PE SoC base is zero\"\);",
            r"sweet_early_mark\(24, \"PE SoC base lookup done\"\);",
            r"sweet_early_mark\(25, \"PE before /cpus lookup\"\);",
            r"sweet_early_mark\(26, \"PE /cpus lookup done\"\);",
            r"sweet_early_mark\(27, \"PE /cpus iterator ready\"\);",
            r"sweet_early_mark\(28, \"PE /cpus frequency scan done\"\);",
            r"sweet_early_mark\(29, \"PE before arm-io lookup\"\);",
            r"sweet_early_mark\(30, \"PE arm-io lookup done\"\);",
            r"sweet_early_mark\(31, \"PE before arm-io device_type\"\);",
            r"sweet_early_mark\(32, \"PE arm-io device_type read done\"\);",
            r"sweet_early_mark\(33, \"PE before arm-io ranges\"\);",
            r"sweet_early_mark\(34, \"PE arm-io ranges read done\"\);",
            r"sweet_early_mark\(35, \"PE arm-io ranges absent; using reg\"\);",
            r"sweet_early_mark\(36, \"PE before arm-io reg\"\);",
            r"sweet_early_mark\(37, \"PE arm-io reg missing\"\);",
            r"sweet_early_mark\(38, \"PE arm-io reg read done\"\);",
            r"whyred synthetic ADT provides arm-io reg, not ranges",
        ],
        "pexpert/gen/device_tree.c": [
            r"#include <arm64/sweet_early.h>",
            r"static unsigned int whyred_find_entry_depth;",
            r"sweet_early_mark\(39, \"SecureDTFindEntry entered\"\);",
            r"sweet_early_mark\(96, \"SecureDTFindEntry returned\"\);",
            r"sweet_early_mark\(40 \+ trace_depth, \"SecureDTFindEntry recursion depth\"\);",
            r"sweet_early_mark\(60 \+ k, \"SecureDTFindEntry root property\"\);",
            r"sweet_early_mark\(80 \+ k, \"SecureDTFindEntry root child\"\);",
            r"sweet_early_hex64\(\"DTRootNode\",",
            r"sweet_early_hex64\(\"DTEnd\",",
            r"sweet_early_hex64\(\"DTSize\",",
            r"sweet_early_mark\(97, \"SecureDTFindEntry root header bounds ok\"\);",
            r"sweet_early_hex64\(\"root nProperties\",",
            r"sweet_early_hex64\(\"root nChildren\",",
            r"sweet_early_mark\(98, \"SecureDTFindEntry root header loaded\"\);",
            r"sweet_early_mark\(99, \"SecureDTFindEntry root property scan starts\"\);",
        ],
        "pexpert/pexpert/arm/protos.h": [
            r"SERIAL_WHYRED_UARTDM\s*=\s*0x40",
        ],
        "config/MASTER.arm64.sweet": [
            r"options\s+WHYRED_UARTDM\b",
        ],
    }
    hashes = {}
    for relative, required in patterns.items():
        content = (root / relative).read_bytes()
        text = content.decode("utf-8")
        for pattern in required:
            if not re.search(pattern, text):
                raise SystemExit(f"Missing whyred source requirement in {relative}: {pattern}")
        hashes[relative] = hashlib.sha256(content).hexdigest()
    board_header = (root / "pexpert/pexpert/arm64/SWEET.h").read_text()
    if not re.search(r"#define\s+SWEET_SMP_MAX_CPUS\s+1\b", board_header):
        raise SystemExit("whyred bring-up must keep the unvalidated heterogeneous cluster disabled")
    cpu_source = (root / "iokit/Kernel/arm/SweetCPU.cpp").read_text()
    for required in (
        'getProperty("logical-cpu-id")', 'getProperty("reg")',
        'WHYRED CPU: start logical=', 'WHYRED CPU: rejected provider properties',
        'WHYRED CPU: rejected reg=', 'topology->boot_cpu->phys_id != 0x100',
        'Kryo 260', 'ml_set_max_cpus(topology->max_cpu_id + 1)',
    ):
        if required not in cpu_source:
            raise SystemExit(f"whyred CPU startup guard/diagnostic is missing: {required}")
    hashes["pexpert/pexpert/arm64/SWEET.h"] = hashlib.sha256(board_header.encode()).hexdigest()
    hashes["iokit/Kernel/arm/SweetCPU.cpp"] = hashlib.sha256(cpu_source.encode()).hexdigest()
    startup = (root / "osfmk/arm64/start.s").read_text().split("LEXT(start_first_cpu)", 1)[1]
    if not (startup.index("WHYRED_UART_WORD 0x30554e58") < startup.index("OSLAR_EL1") <
            startup.index("Lsweet_mark_pixel:")):
        raise SystemExit("UART entry marker must precede OSLAR and framebuffer writes")
    vector_base = startup.rindex("EXT(LowExceptionVectorBase)@page")
    mmu_marker = startup.index("WHYRED_UART_WORD 0x34554e58")
    mmu_enable = startup.index("MSR_SCTLR_EL1_X0")
    first_stage_enable = startup.index("WHYRED_UART_WORD 0x35554e58")
    stage6 = startup.index("WHYRED_UART_WORD 0x36554e58")
    restore_vbar = startup.rindex("EXT(ExceptionVectorsBase)@page")
    if not (vector_base < mmu_marker < mmu_enable < first_stage_enable < stage6 < restore_vbar):
        raise SystemExit("Diagnostic VBAR must span MMU enable and restore before arm_init")
    vector_setups = list(re.finditer(r"adrp\s+x0,\s*EXT\(LowExceptionVectorBase\)@page\b", startup))
    setup = startup[vector_setups[-1].start():mmu_marker]
    physical_setup = (r"adrp\s+x0,\s*EXT\(LowExceptionVectorBase\)@page\s+"
                      r"add\s+x0,\s*x0,\s*EXT\(LowExceptionVectorBase\)@pageoff\s+"
                      r"MSR_VBAR_EL1_X0\s*")
    if not re.fullmatch(physical_setup, setup):
        raise SystemExit("Physical VBAR must use the PC-relative address without another VA/PA conversion")
    arm_init = (root / "osfmk/arm/arm_init.c").read_text()
    checkpoints = [
        'sweet_early_mark(1, "arm_init entered (MMU on)")',
        'sweet_early_mark(10, "arm_setup_pre_sign done")',
        'sweet_early_mark(11, "arm_slide_rebase_and_sign_image done")',
        'sweet_early_mark(12, "boot_args copied")',
        'sweet_early_mark(13, "cpu_data_init done")',
        'sweet_early_mark(14, "before PE_init_platform")',
        'sweet_early_mark(2, "PE_init_platform done")',
    ]
    if [arm_init.index(item) for item in checkpoints] != sorted(
            arm_init.index(item) for item in checkpoints):
        raise SystemExit("arm_init UART checkpoints are missing or out of order")
    pe_init = (root / "pexpert/arm/pe_init.c").read_text().split(
        "PE_init_platform(boolean_t vm_initialized", 1)[1]
    pe_checkpoints = [
        'sweet_early_mark(17, "PE before SecureDTInit")',
        'SecureDTInit(PE_state.deviceTreeHead, PE_state.deviceTreeSize);',
        'sweet_early_mark(18, "PE SecureDTInit done")',
        'pe_identify_machine(boot_args_ptr);',
        'sweet_early_mark(19, "PE identify machine done")',
        'sweet_early_mark(20, "PE init debug done")',
    ]
    if [pe_init.index(item) for item in pe_checkpoints] != sorted(
            pe_init.index(item) for item in pe_checkpoints):
        raise SystemExit("PE_init_platform UART checkpoints are missing or out of order")
    identify = (root / "pexpert/arm/pe_identify_machine.c").read_text()
    identify_body = identify.split("pe_identify_machine(boot_args * bootArgs)", 1)[1].split(
        "vm_offset_t\npe_arm_get_soc_base_phys", 1)[0]
    identify_checkpoints = [
        'sweet_early_mark(21, "pe_identify_machine entered")',
        'sweet_early_mark(22, "PE before SoC base lookup")',
        'sweet_early_mark(23, "PE SoC base is zero")',
        'sweet_early_mark(24, "PE SoC base lookup done")',
        'sweet_early_mark(25, "PE before /cpus lookup")',
        'sweet_early_mark(26, "PE /cpus lookup done")',
        'sweet_early_mark(27, "PE /cpus iterator ready")',
        'sweet_early_mark(28, "PE /cpus frequency scan done")',
    ]
    if [identify_body.index(item) for item in identify_checkpoints] != sorted(
            identify_body.index(item) for item in identify_checkpoints):
        raise SystemExit("pe_identify_machine UART checkpoints are missing or out of order")
    soc_body = identify.split("pe_arm_get_soc_base_phys(void)", 1)[1].split(
        "extern void     fleh_fiq_generic", 1)[0]
    soc_checkpoints = [
        'sweet_early_mark(29, "PE before arm-io lookup")',
        'sweet_early_mark(30, "PE arm-io lookup done")',
        'sweet_early_mark(31, "PE before arm-io device_type")',
        'sweet_early_mark(32, "PE arm-io device_type read done")',
        'sweet_early_mark(33, "PE before arm-io ranges")',
        'sweet_early_mark(34, "PE arm-io ranges read done")',
        'sweet_early_mark(35, "PE arm-io ranges absent; using reg")',
        'sweet_early_mark(36, "PE before arm-io reg")',
        'sweet_early_mark(37, "PE arm-io reg missing")',
        'sweet_early_mark(38, "PE arm-io reg read done")',
    ]
    if [soc_body.index(item) for item in soc_checkpoints] != sorted(
            soc_body.index(item) for item in soc_checkpoints):
        raise SystemExit("SoC lookup UART checkpoints are missing or out of order")
    device_tree = (root / "pexpert/gen/device_tree.c").read_text()
    secure_find_signature = "SecureDTFindEntry(const char *propName, const char *propValue, DTEntry *entryH)"
    recursive_signature = "find_entry(const char *propName, const char *propValue, DTEntry *entryH)"
    secure_find_start = device_tree.index(secure_find_signature)
    recursive_start = device_tree.index(recursive_signature, secure_find_start + len(secure_find_signature))
    find_entry_body = device_tree[secure_find_start + len(secure_find_signature):recursive_start]
    find_entry_checkpoints = [
        'sweet_early_mark(39, "SecureDTFindEntry entered")',
        'startingP = (char const *)DTRootNode;',
        'whyred_find_entry_depth = 0;',
        'result = find_entry(propName, propValue, entryH);',
        'sweet_early_mark(96, "SecureDTFindEntry returned")',
    ]
    if [find_entry_body.index(item) for item in find_entry_checkpoints] != sorted(
            find_entry_body.index(item) for item in find_entry_checkpoints):
        raise SystemExit("SecureDTFindEntry UART checkpoints are missing or out of order")
    recursive_body = device_tree[recursive_start:]
    recursion_checkpoints = [
        'unsigned int trace_depth = whyred_find_entry_depth++;',
        'sweet_early_mark(40 + trace_depth, "SecureDTFindEntry recursion depth")',
        'ASSERT_HEADER_IN_DT(nodeP, sizeof(DeviceTreeNode));',
        'sweet_early_mark(97, "SecureDTFindEntry root header bounds ok");',
        'sweet_early_mark(98, "SecureDTFindEntry root header loaded");',
        'sweet_early_mark(99, "SecureDTFindEntry root property scan starts");',
        'sweet_early_mark(60 + k, "SecureDTFindEntry root property")',
        'sweet_early_mark(80 + k, "SecureDTFindEntry root child")',
    ]
    if [recursive_body.index(item) for item in recursion_checkpoints] != sorted(
            recursive_body.index(item) for item in recursion_checkpoints):
        raise SystemExit("SecureDTFindEntry recursive UART checkpoints are missing or out of order")
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if args.expected_upstream_commit and commit != args.expected_upstream_commit:
        raise SystemExit(f"Unexpected upstream XNU commit: {commit}")
    report = {
        "source_commit": commit, "source_sha256": hashes,
        "framebuffer": {"physical_base": "0x9d400000", "width": 1080,
                        "height": 2160, "stride": 4320,
                        "l2_block_base": "0x9c000000", "alias_offset": "0x01400000"},
        "uartdm": {"physical_base": "0x0c170000", "baud": 115200,
                   "mode": "firmware-configured 8-N-1", "direction": "TX-only PIO",
                   "entry_marker": "XNU0 before OSLAR and framebuffer", "tx_idle_wait": True},
        "whyred_cpu": {"boot_mpidr": "0x100", "smp_topology_limit": 1,
                       "cpu_start_diagnostics": True,
                       "secondary_startup_hardware_validated": False},
        "pe_identify_machine_uart_markers": list(range(21, 39)),
        "secure_device_tree_find_trace": {"entry": 39, "depth_markers": [40, 55],
                                           "root_property_markers": [60, 75],
                                           "root_child_markers": [80, 95], "returned": 96},
        "secure_device_tree_bounds_trace": {"pre_assert_values": ["DTRootNode", "DTEnd", "DTSize"],
                                             "header_bounds_ok": 97, "root_header_loaded": 98,
                                             "root_property_scan_starts": 99},
        "bootstrap_uart": {"stages": ["XNU" + str(i) for i in range(7)],
                           "device_block_base": "0x0c000000", "memory_type": "Device-nGnRnE",
                           "exception_registers": ["ESR_EL1", "ELR_EL1", "FAR_EL1"],
                           "vbar_spans_mmu": True,
                           "vbar_physical_pc_relative": True,
                           "c_stages": True},
        "result": "whyred framebuffer and UARTDM requirements passed",
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(report["result"])


if __name__ == "__main__":
    main()

