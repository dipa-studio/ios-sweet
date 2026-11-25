#!/usr/bin/env python3
"""Replay verified Xcode 15 IIG output for unchanged xnu-8796 interfaces.

Xcode 16 generates a newer IORPC ABI. Keep the original generated source
instead of changing the kernel's RPC ABI as part of a build-host migration.
The companion cache records the successful workflow artifact and hashes of
the DriverKit source interfaces/headers. Any tracked input drift fails the build.
"""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--def", dest="definition", type=Path, required=True)
    parser.add_argument("--header", type=Path, required=True)
    parser.add_argument("--impl", type=Path, required=True)
    parser.add_argument("--framework-name", required=True)
    options, compiler_flags = parser.parse_known_args()
    if options.framework_name != "DriverKit":
        parser.error("The verified cache only supports DriverKit")
    if compiler_flags and compiler_flags[0] != "--":
        parser.error("Unknown IIG options: " + " ".join(compiler_flags))

    definition = options.definition.resolve()
    root = definition.parents[2]
    cache_path = Path(__file__).with_name("iig-8796-cache.json.gz")
    with gzip.open(cache_path, "rt", encoding="utf-8") as stream:
        cache = json.load(stream)
    relative = definition.relative_to(root).as_posix()
    if relative not in cache["definitions"]:
        parser.error("Interface absent from verified IIG cache: " + relative)
    for name, expected in cache["inputs"].items():
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            parser.error("IIG input changed; regenerate the cache with compatible iig: " + name)

    entry = cache["definitions"][relative]
    for kind, destination in (("header", options.header), ("impl", options.impl)):
        data = entry[kind]["content"].encode("utf-8")
        if hashlib.sha256(data).hexdigest() != entry[kind]["sha256"]:
            parser.error("Corrupt cached IIG output: " + relative)
        destination.write_bytes(data)
    print("Verified Xcode 15 IIG cache: " + definition.name, file=sys.stderr)


if __name__ == "__main__":
    main()
