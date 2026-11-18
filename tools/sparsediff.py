#!/usr/bin/env python3
"""Write an Android sparse image holding only the blocks where NEW differs from OLD.

  sparsediff.py OLD.img NEW.img OUT.simg [--block 4096]

OLD must be exactly what the partition holds now (the image last flashed);
NEW is the edited copy. Differing blocks become RAW chunks, everything else
DONT_CARE, so `fastboot flash PART OUT.simg` rewrites only the changes
instead of the whole image. Both images must be the same size.
"""
import argparse, os, struct, sys

MAGIC = 0xed26ff3a
RAW, DONT_CARE = 0xcac1, 0xcac3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('old'); ap.add_argument('new'); ap.add_argument('out')
    ap.add_argument('--block', type=int, default=4096)
    a = ap.parse_args()
    bs = a.block
    size = os.path.getsize(a.new)
    if os.path.getsize(a.old) != size or size % bs:
        sys.exit('images must have the same size, a multiple of the block size')
    nblocks = size // bs

    # Pass 1: runs of (differs, count) at block granularity, streamed in 8 MiB reads.
    runs = []
    step = (8 << 20) // bs
    with open(a.old, 'rb') as fo, open(a.new, 'rb') as fn:
        for base in range(0, nblocks, step):
            n = min(step, nblocks - base)
            bo, bn = fo.read(n * bs), fn.read(n * bs)
            for i in range(n):
                d = bo[i * bs:(i + 1) * bs] != bn[i * bs:(i + 1) * bs]
                if runs and runs[-1][0] == d:
                    runs[-1][1] += 1
                else:
                    runs.append([d, 1])

    # Pass 2: emit chunks, copying the differing blocks from NEW.
    changed = sum(c for d, c in runs if d)
    with open(a.new, 'rb') as fn, open(a.out, 'wb') as out:
        out.write(struct.pack('<IHHHHIIII', MAGIC, 1, 0, 28, 12, bs, nblocks, len(runs), 0))
        pos = 0
        for d, count in runs:
            if d:
                out.write(struct.pack('<HHII', RAW, 0, count, 12 + count * bs))
                fn.seek(pos * bs)
                left = count * bs
                while left:
                    chunk = fn.read(min(left, 8 << 20))
                    out.write(chunk)
                    left -= len(chunk)
            else:
                out.write(struct.pack('<HHII', DONT_CARE, 0, count, 12))
            pos += count
    print(f'{a.out}: {changed} of {nblocks} blocks changed '
          f'({changed * bs >> 20} MiB) in {sum(1 for d, _ in runs if d)} runs')


if __name__ == '__main__':
    main()
