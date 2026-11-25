#!/bin/bash
# Pinned, portable constant-time AES for the SWEET legacy CBC/ECB API.
set -euo pipefail
[[ "${MACHINE_CONFIG:-}" == SWEET ]] || exit 0
[[ -f libkern/crypto/corecrypto_aes.c ]] || exit 1
bearssl_sha=7bea48e5e850ab4cafbe68d3765cdaba13a86d6f
bearssl_tmp=$(mktemp -d)
trap 'rm -rf "$bearssl_tmp"' EXIT
git init -q "$bearssl_tmp"
# The upstream host can return502. Retry finitely, then use the mirror at
# exactly the same pinned commit; never substitute a branch or newer version.
bearssl_fetched=0
for bearssl_remote in https://www.bearssl.org/git/BearSSL \
    https://github.com/status-im/BearSSL.git; do
    for bearssl_attempt in 1 2; do
        if git -C "$bearssl_tmp" fetch -q --depth 1 "$bearssl_remote" "$bearssl_sha"; then
            if [[ "$(git -C "$bearssl_tmp" rev-parse FETCH_HEAD)" == "$bearssl_sha" ]]; then
                bearssl_fetched=1
                break 2
            fi
        fi
        echo "BearSSL fetch failed ($bearssl_remote, attempt$bearssl_attempt)" >&2
        if [[ "$bearssl_attempt" == 1 ]]; then sleep 2; fi
    done
done
[[ "$bearssl_fetched" == 1 ]] || { echo "Pinned BearSSL unavailable" >&2; exit 1; }
git -C "$bearssl_tmp" checkout -q FETCH_HEAD
[[ "$(git -C "$bearssl_tmp" rev-parse HEAD)" == "$bearssl_sha" ]]
python3 - "$bearssl_tmp" <<'PY'
from pathlib import Path
import shutil
import sys

source = Path(sys.argv[1])
target = Path('libkern/crypto/sweet_bearssl')
if target.exists():
    raise SystemExit(f'refusing to overwrite existing AES source: {target}')
shutil.copytree(source / 'inc', target / 'inc')
(target / 'src/symcipher').mkdir(parents=True)
for file in ('inner.h', 'config.h'):
    shutil.copy2(source / 'src' / file, target / 'src' / file)
# XNU exports machine/limits.h instead of the userspace limits.h.
header = target / 'src/inner.h'
text = header.read_text()
assert text.count('#include <limits.h>') == 1
header.write_text(text.replace('#include <limits.h>',
    '#if defined(KERNEL)\n#include <machine/limits.h>\n'
    '#else\n#include <limits.h>\n#endif'))
for name in ('aes_ct', 'aes_ct_enc', 'aes_ct_dec', 'aes_ct_cbcenc', 'aes_ct_cbcdec'):
    shutil.copy2(source / 'src/symcipher' / (name + '.c'),
                 target / 'src/symcipher' / (name + '.c'))
# MD5, SHA-1 and SHA-384/512 for the legacy hash APIs, with their codecs.
for name in ('hash/md5.c', 'codec/dec32le.c', 'codec/enc32le.c',
             'hash/sha1.c', 'codec/dec32be.c', 'codec/enc32be.c',
             'hash/sha2big.c', 'codec/dec64be.c', 'codec/enc64be.c'):
    (target / 'src' / name).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / 'src' / name, target / 'src' / name)
shutil.copy2(source / 'LICENSE.txt', target / 'LICENSE.txt')
PY
echo "Staged BearSSL portable AES, MD5, SHA-1 and SHA-384/512 ($bearssl_sha) for SWEET"
