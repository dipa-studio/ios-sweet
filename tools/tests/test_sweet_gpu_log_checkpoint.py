"""Run the kernel's checkpoint flush code against a bounded UFS device."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PRELUDE = r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <string.h>
#include <errno.h>
#define UFS_BLOCK 4096u
#define SWEET_LOG_SIZE (4u << 20)
#define SWEET_LOG_BLOCKS (1 + SWEET_LOG_SIZE / UFS_BLOCK)
#define BOUNCE_SIZE (128u << 10)
#define DMA_BOUNCE 0
#define MIN(a,b) ((a)<(b)?(a):(b))
#define bzero(p,n) memset(p,0,n)
#define os_atomic_load(p,o) atomic_load_explicit(p,memory_order_##o)
#define os_atomic_store(p,v,o) atomic_store_explicit(p,v,memory_order_##o)
static char sweet_log_ring[SWEET_LOG_SIZE];
static _Atomic uint64_t sweet_log_total;
static _Atomic uint32_t sweet_log_has_flushed;
static uint64_t sweet_log_flushed, sweet_log_sequence;
static unsigned char bounce[BOUNCE_SIZE], disk[SWEET_LOG_BLOCKS*UFS_BLOCK];
static struct { uintptr_t dma; uint64_t first_block,nblocks; } su;
struct sweet_log_header { char magic[8]; uint32_t version,size; uint64_t total,seq; };
static int sweet_ufs_lock, fail_write, fail_sync, writes, syncs;
static void lck_mtx_lock(int *p) { assert(!*p); *p=1; }
static void lck_mtx_unlock(int *p) { assert(*p); *p=0; }
static int ufs_write_blocks_checked(uint64_t lba,uint32_t n,bool data) {
    assert(sweet_ufs_lock && data);
    uint64_t base=su.first_block+su.nblocks-SWEET_LOG_BLOCKS;
    assert(lba>=base && lba+n<=base+SWEET_LOG_BLOCKS && n*UFS_BLOCK<=BOUNCE_SIZE);
    writes++; if(fail_write) return EIO;
    memcpy(disk+(lba-base)*UFS_BLOCK,bounce,n*UFS_BLOCK); return 0;
}
static int ufs_sync_cache(void) { assert(sweet_ufs_lock); syncs++; return fail_sync?EIO:0; }
'''
HARNESS = r'''
int main(void) {
    assert(sweet_gpu_log_flush()==ENXIO && !writes);
    su.dma=(uintptr_t)bounce; su.first_block=100; su.nblocks=5000;
    assert(!sweet_gpu_log_flush() && !writes && !syncs);
    for(unsigned i=0;i<SWEET_LOG_SIZE;i++)sweet_log_ring[i]=(char)(i%251);
    sweet_log_total=7;
    assert(!sweet_gpu_log_flush() && sweet_log_flushed==7 && sweet_log_has_flushed);
    assert(writes==2 && syncs==1 && sweet_log_sequence==1);
    struct sweet_log_header *h=(void*)disk;
    assert(!memcmp(h->magic,"SWEETLOG",8) && h->total==7 && h->seq==1);
    assert(!memcmp(disk+UFS_BLOCK,sweet_log_ring,UFS_BLOCK));
    assert(!sweet_gpu_log_flush() && writes==2);
    sweet_log_total=SWEET_LOG_SIZE+6000;
    assert(!sweet_gpu_log_flush() && sweet_log_flushed==sweet_log_total);
    assert(h->total==sweet_log_total && h->seq==2);
    assert(!memcmp(disk+UFS_BLOCK,sweet_log_ring,SWEET_LOG_SIZE));
    sweet_log_total+=64; fail_write=1;
    uint64_t saved=sweet_log_flushed;
    assert(sweet_gpu_log_flush()==EIO && sweet_log_flushed==saved && sweet_log_sequence==2);
    assert(!sweet_ufs_lock);
    fail_write=0; fail_sync=1;
    assert(sweet_gpu_log_flush()==EIO && sweet_log_flushed==saved && sweet_log_sequence==2);
    fail_sync=0;
    assert(!sweet_gpu_log_flush() && sweet_log_flushed==sweet_log_total && sweet_log_sequence==3);
    assert(h->total==sweet_log_total && h->seq==3 && !sweet_ufs_lock);
    return 0;
}
'''


class CheckpointTests(unittest.TestCase):
    def test_actual_flush_bounds_wrap_and_failed_sync(self):
        patch = (ROOT / 'xnu/patches/0210-matisse-csf-vm-checkpoints.patch').read_text()
        section = patch.split('diff --git a/bsd/dev/sweet_ufs.c', 1)[1].split('diff --git ', 1)[0]
        source = '\n'.join(line[1:] for line in section.splitlines()
                           if line.startswith(('+', ' ')) and not line.startswith('+++'))
        code = 'int\nsweet_gpu_log_flush(void)\n{' + source.split('int\nsweet_gpu_log_flush(void)\n{', 1)[1].split('\n}', 1)[0] + '\n}\n'
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'test.c').write_text(PRELUDE + code + HARNESS)
            subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', str(p / 'test.c'),
                            '-o', str(p / 'test')], check=True)
            subprocess.run([str(p / 'test')], check=True)


if __name__ == '__main__':
    unittest.main()
