#!/usr/bin/env python3
"""Package an eMMC APFS-root userspace boot candidate; never flashes the handset."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

PORT = Path(__file__).resolve().parents[1]
SYSTEM_PARTITION_BYTES = 6_291_456 * 512
BOOT_PARTITION_BYTES = 64 * 1024 * 1024


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_sums(path):
    result = {}
    for line in path.read_text().splitlines():
        fields = line.split(None, 1)
        if len(fields) == 2:
            result[fields[1].strip().lstrip("*")] = fields[0]
    return result


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: package-whyred-ios-root-v54.py RUN_ID ARTIFACT_SHA256 SOURCE_COMMIT")
    run, digest, commit = sys.argv[1:]
    if (not run.isdigit() or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or not re.fullmatch(r"[0-9a-f]{40}", commit)):
        raise SystemExit("invalid run, artifact digest or source commit")

    ci = PORT / f"out/ci-kernel-no-lse-{run}"
    archive = PORT / f"out/build-inputs/run-{run}-kernel.zip"
    if not archive.is_file() or sha(archive) != digest:
        raise SystemExit("Actions artifact digest mismatch")
    kernel = ci / "kernel.development.sweet"
    sums = sha_sums(ci / "SHA256SUMS")
    for name in (kernel.name, "whyred-var.hfs"):
        file = ci / name
        if not file.is_file() or sums.get(name) != sha(file):
            raise SystemExit(f"CI artifact checksum mismatch: {name}")
    log = (ci / "build.log").read_text(errors="replace")
    for number in range(115, 140):
        marker = f"{number:04d}-"
        if not re.search(r"Applying patch: [^\r\n]*" + marker, log):
            raise SystemExit(f"patch {marker} was not confirmed in CI")
        if re.search(r"Skipping patch [^\r\n]*" + marker, log):
            raise SystemExit(f"patch {marker} was skipped")
    if re.search(r"(?m)^[^\n|]*:\d+:\d+: (?:fatal )?error:", log):
        raise SystemExit("compiler error in CI log")

    report = json.loads((ci / "whyred-apfs-source-report.json").read_text())
    if report.get("read_only") is not True or report.get("root_opt_in") != "whyred-apfs-root=1":
        raise SystemExit("APFS guard did not confirm read-only, opt-in root mounting")

    var_image = ci / "whyred-var.hfs"
    if var_image.stat().st_size != 32 * 1024 * 1024:
        raise SystemExit("runtime HFS image is not 32 MiB")
    with var_image.open("rb") as stream:
        stream.seek(1024)
        if stream.read(2) != b"H+":
            raise SystemExit("runtime image is not a raw HFS+ filesystem")

    root_image = PORT / "out/whyred-rootfs-prep/whyred-system-ios165-v54.apfs"
    if not root_image.is_file() or root_image.stat().st_size > SYSTEM_PARTITION_BYTES:
        raise SystemExit("local APFS system image is missing or exceeds the system partition")
    root_sums = sha_sums(root_image.with_suffix(root_image.suffix + ".sha256"))
    if root_sums.get(root_image.name) != sha(root_image):
        raise SystemExit("local APFS system image checksum mismatch")
    manifest = (PORT / "out/whyred-rootfs-prep/system.whyred.build.manifest").read_text()
    cache_link = "System/Library/Caches/com.apple.dyld\t/System/Cryptexes/OS/System/Library/Caches/com.apple.dyld"
    if cache_link not in manifest:
        raise SystemExit("root manifest is missing the dyld-cache link used by ignition")

    subprocess.run([sys.executable, str(PORT / "tools/audit-arm64-lse.py"), str(kernel),
                    "--require-none", "--require-no-pan"], check=True)

    base = PORT / "out/whyred-emmc-block-v49-40949733049"
    stock = PORT.parent / "device-backups/boot.img"
    if sha(stock) != "7aaa6094c477e4def3638a5a58fc7be063a2bb2661d16ad3305b01bebbd25a0f":
        raise SystemExit("stock boot backup changed")
    sys.path.insert(0, str(PORT / "tools"))
    import mkpayload
    import mkbootimg_whyred_legacy as boot
    boot.verify(base / "shim-boot-whyred-uartdm-debug.img", stock,
                base / "shim/Image", base / "payload.bin", BOOT_PARTITION_BYTES)

    out = PORT / f"out/whyred-ios-root-v54-{run}"
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    (out / "shim").mkdir(parents=True)
    for src, dest in [
        (kernel, "kernel.development.whyred"),
        (root_image, "whyred-system-ios165.apfs"),
        (var_image, "whyred-var.hfs"),
        (base / "shim/Image", "shim/Image"),
        (base / "whyred-gold.adt", "whyred-gold.adt"),
    ]:
        shutil.copyfile(src, out / dest)

    command = (
        "debug=0xc serial=1 cpus=1 keepsyms=1 -noprogress -whyred-platform "
        "rd=whyredemmc0 whyred-emmc-block=1 whyred-emmc-partition=system "
        "whyred-apfs-root=1 whyred-var-md0=1 ignition_level=1 "
        "unentitled_ios_sim_launch=1"
    )
    if len(command.encode()) >= 608:
        raise SystemExit("kernel command line exceeds the boot-args buffer")
    payload, info = mkpayload.build(
        str(out / "kernel.development.whyred"), str(out / "whyred-gold.adt"),
        command, ramdisk_path=str(out / "whyred-var.hfs"))
    (out / "payload.bin").write_bytes(payload)
    image = out / "shim-boot-whyred-uartdm-debug.img"
    boot.build(stock, out / "shim/Image", out / "payload.bin", image, BOOT_PARTITION_BYTES)
    if image.stat().st_size > BOOT_PARTITION_BYTES:
        raise SystemExit("boot image exceeds the 64 MiB boot partition")
    verification = boot.verify(image, stock, out / "shim/Image", out / "payload.bin", BOOT_PARTITION_BYTES)
    (out / "verification.txt").write_text(verification + "\n")

    details = {
        "run": run,
        "source_commit": commit,
        "actions_artifact_sha256": digest,
        "cmdline": command,
        "ramdisk": info["ramdisk"],
        "kernel_sha256": sha(out / "kernel.development.whyred"),
        "system_apfs_sha256": sha(out / "whyred-system-ios165.apfs"),
        "var_hfs_sha256": sha(out / "whyred-var.hfs"),
        "image_sha256": sha(image),
        "adt_sha256": sha(out / "whyred-gold.adt"),
        "hardware_test": "not yet tested; next image selects read-only eMMC system APFS root and mounts RAM HFS at /private/var",
        "flashed_partition": "none",
        "system_partition_written": False,
        "contains_local_apple_ios_userland": True,
    }
    (out / "manifest.json").write_text(json.dumps(details, indent=2) + "\n")
    print("v54 eMMC APFS-root candidate packaged; no device operation was performed")
    print(image)
    print(details["image_sha256"])


if __name__ == "__main__":
    main()

