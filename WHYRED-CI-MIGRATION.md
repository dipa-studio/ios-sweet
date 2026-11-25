# Whyred CI migration to macOS 15

The workflow uses macos-15 with Xcode 16.4. GitHub's macOS 14 brownout on 2026-10-26 prevented earlier jobs from obtaining a runner; full retirement is scheduled for November 2.

Run 40346688944 obtained a macOS 15 runner, then compilation failed. Its buildtree contains DriverKit-427 IIG output using IORPC.kernelContent, absent from xnu-8796.

The IIG adapter preserves the older RPC ABI by replaying Xcode 15 generated sources from successful run 40334160445. The cache records the artifact provenance and checks 40 source inputs plus every generated output digest. Local validation reproduced 34 output files for 17 interfaces byte-for-byte and rejected changed input. The user authorized publishing this cache and adapter.

The follow-up workflow saves build.log in its artifact. A successful full build is still required before packaging a new boot image.

## Hosted ARM64 capacity

Run 40350616642 attempt 1 executed no steps. GitHub annotations report: "Due to capacity constraints, jobs targeting macOS arm64 runners may experience longer queue times" and "The job was not acquired by Runner of type hosted even after multiple attempts", plus an internal server error. No active workflows were found in the account's nine accessible repositories during diagnosis.

The default build host is now the standard macos-15-intel pool, with macos-15 available as a manual runner_image choice. The target remains ARM64 and Xcode stays pinned to 16.4. This changes the machine pool used to build the kernel; a successful Intel-hosted full build remains to be verified.

## Physical bootstrap VBAR correction

Before flashing v4, audit found that ADRP/ADD was followed by another VA-to-PA conversion while already executing with the MMU off. Remove that extra conversion: the PC-relative address is already physical. Keep the normal high-vector restoration before arm_init. The source guard now requires this direct setup; local compilation of all five diagnostic units passed, and a negative check rejected the old setup. Boot-image packaging also checks the compiled ADRP/ADD/MSR sequence before XNU4.
