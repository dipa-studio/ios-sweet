# APFS image builder

`mkapfs.py` is copied from HakiOS at commit
`88513176b1e96ecf0b764cd62c6f4e6ac71345e3`, path `tools/apfs/mkapfs.py`.
Source: https://github.com/oosexgang/hakios-xnu-kernel/blob/88513176b1e96ecf0b764cd62c6f4e6ac71345e3/tools/apfs/mkapfs.py
It is distributed under the upstream repository's APSL 2.0 license, retained
as `LICENSE.APSL`. It builds local unencrypted APFS test images using Python's
standard library. No Apple firmware, iOS filesystem or device dump is included.

`../test-whyred-apfs.py --source XNU_ROOT` creates synthetic test files, makes
an image with this builder, and checks contents/errors with the exact C format
reader included in the kernel patch. The host test uses system zlib/OpenSSL
(Windows uses the explicit host adapters in `../apfs-host-windows`).

`../mkapfs-test-root.py --init sweet-init.macho --output root.apfs` builds a
small diagnostic filesystem with the project's static PID 1 at `/sbin/launchd`.
This is a filesystem/exec probe; it does not contain iOS launchd or SpringBoard.
