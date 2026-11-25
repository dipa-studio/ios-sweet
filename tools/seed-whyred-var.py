#!/usr/bin/env python3
"""Seed the ephemeral whyred /private/var image for the built-in AKS provider."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import stat

# Required by tools/mkiosroot.sh and sweet-root-tweaks.py in the same project.
OVERRIDES = {
    "keybags": (0, 0, 0o700),
    "root": (0, 0, 0o700),
    "empty": (0, 0, 0o555),
    "root/Library/Caches": (0, 0, 0o700),
    "root/Library/Logs": (0, 0, 0o700),
    "mobile/tmp": (501, 501, 0o700),
    "mobile/Containers/Data": (501, 501, 0o755),
    "mobile/Containers/Shared": (501, 501, 0o755),
    "db/diagnostics": (272, 272, 0o751),
    "db/diagnostics/timesync": (272, 272, 0o755),
    "db/uuidtext": (272, 272, 0o755),
    "containers/Bundle": (33, 33, 0o755),
    "containers/Data/System": (0, 0, 0o755),
    "containers/Shared/SystemGroup": (0, 0, 0o755),
    "containers/Temp": (0, 0, 0o755),
    "mobile/Library/Preferences": (501, 501, 0o755),
    "mobile/Library/Caches": (501, 501, 0o755),
    "mobile/Library/Logs": (501, 501, 0o755),
    "mobile/Media": (501, 501, 0o755),
    "root/Library/Preferences": (0, 0, 0o755),
}
LAYOUT = json.loads(Path(__file__).with_name("whyred-var-layout.json").read_text(encoding="utf-8"))
DIRECTORIES = {r["path"]: (r["uid"], r["gid"], int(r["mode"], 8)) for r in LAYOUT["directories"]}
DIRECTORIES.update(OVERRIDES)
SYMLINKS = {
    "db/timezone/zoneinfo": "/usr/share/zoneinfo.default",
    "db/timezone/localtime": "/var/db/timezone/zoneinfo/Etc/UTC",
}

BUILD = "20F66"
PREFERENCES = {
    "mobile/Library/Preferences/com.apple.migration.plist": {
        "LastSystemVersion": BUILD,
        "DMUserDataDisposition": {"SyntheticDidUpgrade": False, "buildVersion": BUILD},
    },
    "mobile/Library/Preferences/com.apple.springboard.plist": {
        "BKNoWatchdogs": True,
        "FBLaunchWatchdogExceptions": {"com.apple.purplebuddy": 100.0},
    },
}

MARKERS = (
    "db/diagnostics/.migrated",
    "db/diagnostics/timesync/.migrated",
    "db/uuidtext/.migrated",
)

# Jobs that cannot run in this bring-up because the matching platform/data services
# are not present. launchd reads these persistent overrides before submitting jobs.
DISABLED_JOBS = {
    "com.apple.ScreenTimeAgent": {"Disabled": True},
    "com.apple.icloud.findmydeviced": {"Disabled": True},
    "com.apple.installcoordinationd": {"Disabled": True},
    "com.apple.installcoordination_proxy": {"Disabled": True},
}
DISABLED_JOBS_PATH = "db/com.apple.xpc.launchd/disabled.plist"


def checked_path(root, relative, follow_leaf=True):
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError(f"unsafe image path: {relative}")
    path = root / relative
    resolved = path.resolve() if follow_leaf else path.parent.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"path escapes mounted image: {relative}")
    return path


def metadata(path, uid, gid, mode):
    st = path.stat()
    if (st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode)) != (uid, gid, mode):
        raise ValueError(f"incorrect owner or mode: {path.name}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mountpoint", type=Path)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    root = args.mountpoint.resolve()
    if root in (Path("/"), Path("/private/var")) or not all(
            (root / item).is_dir() for item in ("db", "mobile", "root", "tmp")):
        raise SystemExit("expected a mounted, initialized whyred var image")
    if not args.verify:
        if os.geteuid() != 0:
            raise SystemExit("run this image seeding step as root")
        for relative, (uid, gid, mode) in DIRECTORIES.items():
            path = checked_path(root, relative)
            path.mkdir(parents=True, exist_ok=True)
            os.chown(path, uid, gid)
            os.chmod(path, mode)
        for relative, target in SYMLINKS.items():
            path = checked_path(root, relative, follow_leaf=False)
            if path.is_symlink() and os.readlink(path) != target:
                path.unlink()
            if not path.is_symlink():
                if path.exists():
                    raise ValueError(f"expected a symlink, found existing data: {relative}")
                path.symlink_to(target)
            os.lchown(path, 0, 0)
        # SWEET is the existing unlocked AKS provider's synthetic bag payload.
        # This file contains no passcode or device key material.
        bag = checked_path(root, "keybags/systembag.kb")
        with bag.open("wb") as stream:
            plistlib.dump({"KeyBagKeys": b"SWEET"}, stream, fmt=plistlib.FMT_XML)
        os.chown(bag, 0, 0)
        os.chmod(bag, 0o600)
        for relative, values in PREFERENCES.items():
            path = checked_path(root, relative)
            with path.open("wb") as stream:
                plistlib.dump(values, stream, fmt=plistlib.FMT_XML)
            os.chown(path, 501, 501)
            os.chmod(path, 0o600)
        for relative in MARKERS:
            path = checked_path(root, relative)
            path.touch()
            os.chown(path, 272, 272)
            os.chmod(path, 0o644)
        disabled = checked_path(root, DISABLED_JOBS_PATH)
        with disabled.open("wb") as stream:
            plistlib.dump(DISABLED_JOBS, stream, fmt=plistlib.FMT_BINARY, sort_keys=True)
        os.chown(disabled, 0, 0)
        os.chmod(disabled, 0o644)
    for relative, (uid, gid, mode) in DIRECTORIES.items():
        path = checked_path(root, relative)
        if not path.is_dir():
            raise ValueError(f"required directory missing: {relative}")
        metadata(path, uid, gid, mode)
    for relative, target in SYMLINKS.items():
        path = checked_path(root, relative, follow_leaf=False)
        st = path.lstat()
        if not path.is_symlink() or os.readlink(path) != target or (st.st_uid, st.st_gid) != (0, 0):
            raise ValueError(f"incorrect time-zone symlink: {relative}")
    bag = checked_path(root, "keybags/systembag.kb")
    metadata(bag, 0, 0, 0o600)
    with bag.open("rb") as stream:
        if plistlib.load(stream) != {"KeyBagKeys": b"SWEET"}:
            raise ValueError("synthetic system keybag does not match the AKS provider")
    for relative, expected in PREFERENCES.items():
        path = checked_path(root, relative)
        metadata(path, 501, 501, 0o600)
        with path.open("rb") as stream:
            if plistlib.load(stream) != expected:
                raise ValueError(f"incorrect bring-up preferences: {relative}")
    for relative in MARKERS:
        path = checked_path(root, relative)
        metadata(path, 272, 272, 0o644)
        if path.stat().st_size != 0:
            raise ValueError(f"logd migration marker is not empty: {relative}")
    disabled = checked_path(root, DISABLED_JOBS_PATH)
    metadata(disabled, 0, 0, 0o644)
    with disabled.open("rb") as stream:
        if plistlib.load(stream) != DISABLED_JOBS:
            raise ValueError("launchd disabled-job overrides do not match the bring-up profile")
    print(json.dumps({"required_directories": len(DIRECTORIES), "keybag": "verified",
                      "logd_migration_markers": len(MARKERS), "timezone_links": len(SYMLINKS),
                      "bringup_preferences": len(PREFERENCES), "disabled_launchd_jobs": len(DISABLED_JOBS),
                      "owners_and_modes": "verified"}))


if __name__ == "__main__":
    main()
