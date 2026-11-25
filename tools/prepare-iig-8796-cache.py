#!/usr/bin/env python3
"""Extract the verified Xcode 15 IIG source outputs from the preserved CI tree."""

import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import zipfile


def main():
    port = Path(__file__).resolve().parents[1]
    archive = port / "out/build-inputs/xnu-buildtree-40334160445.zip"
    expected = "66c1719f4be6d1bec87c7320a074fd87f3cf63e4d21eef110bbd5b508f666b52"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise SystemExit("The preserved successful CI buildtree digest does not match")
    with zipfile.ZipFile(archive) as zipped:
        tree = tarfile.open(fileobj=io.BytesIO(zipped.read("buildtree.tgz")), mode="r:gz")
    entries = {m.name: m for m in tree.getmembers() if m.isfile()}

    def read(name):
        return tree.extractfile(entries[name]).read()

    cache = {
        "provenance": {
            "repository": "timosid/ios-sweetwhyred",
            "run_id": 40334160445,
            "commit": "516e4b6b1a91cbeb665434cf137d22c316c1a98c",
            "artifact_id": 12657066661,
            "artifact_sha256": expected,
            "generator": "DriverKit-286 (Xcode 15)",
            "purpose": "Preserve the xnu-8796 IORPC ABI on newer build hosts",
        },
        "inputs": {},
        "definitions": {},
    }
    for name in sorted(entries):
        if (name.startswith("xnu/iokit/DriverKit/") and name.endswith((".iig", ".h"))) or name in (
            "xnu/iokit/DriverKit/Makefile", "xnu/iokit/IOKit/IORPC.h"
        ):
            cache["inputs"][name[4:]] = hashlib.sha256(read(name)).hexdigest()
    prefix = "build/xnu.obj/DEVELOPMENT_ARM64_SWEET/iokit/DriverKit/"
    for name in sorted(entries):
        if not name.startswith(prefix) or not name.endswith(".iig.cpp"):
            continue
        basename = name[len(prefix):-8]
        definition = "iokit/DriverKit/" + basename + ".iig"
        if definition not in cache["inputs"]:
            raise SystemExit("Missing IIG input: " + definition)
        outputs = {}
        for kind, source in (("header", prefix + basename + ".h"), ("impl", name)):
            data = read(source)
            if b"iig(DriverKit-286" not in data or b"kernelContent" in data:
                raise SystemExit("Unexpected IIG generator output: " + source)
            outputs[kind] = {"sha256": hashlib.sha256(data).hexdigest(), "content": data.decode("utf-8")}
        cache["definitions"][definition] = outputs
    expected_interfaces = {name for name in cache["inputs"] if name.endswith(".iig")}
    if set(cache["definitions"]) != expected_interfaces or len(expected_interfaces) != 17:
        raise SystemExit("Expected all 17 generated DriverKit interfaces")
    output = port / "tools/iig-8796-cache.json.gz"
    encoded = json.dumps(cache, sort_keys=True, separators=(",", ":")).encode("utf-8")
    output.write_bytes(gzip.compress(encoded, mtime=0))
    print(f"{output.name}: {len(cache['definitions'])} interfaces, {len(cache['inputs'])} inputs, {output.stat().st_size} bytes")
    print("SHA-256:", hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
