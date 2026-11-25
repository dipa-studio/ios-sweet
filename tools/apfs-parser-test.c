/* Synthetic-image tests for the exact APFS format reader included in XNU. */
#include "apfs_lib.h"
#include <inttypes.h>
#define CHECK(c) do { if (!(c)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #c); return 1; } } while (0)
struct disk { uint8_t *bytes; size_t size; unsigned reads; bool fail; };
static int read_disk(void *ctx, uint64_t off, void *buf, size_t len) {
    struct disk *d = ctx;
    d->reads++;
    if (d->reads > 10000 || d->fail || off > d->size || len > d->size - off) return EIO;
    memcpy(buf, d->bytes + (size_t)off, len);
    return 0;
}
static uint8_t *load(const char *path, size_t *size) {
    FILE *f = fopen(path, "rb"); uint8_t *p;
    if (!f) return NULL;
    fseek(f, 0, SEEK_END); *size = (size_t)ftell(f); rewind(f);
    p = malloc(*size ? *size : 1);
    if (!p || fread(p, 1, *size, f) != *size) { free(p); p = NULL; }
    fclose(f); return p;
}
static int list_one(void *ctx, const char *name, size_t len, uint64_t id, uint8_t type) {
    unsigned *mask = ctx; (void)id; (void)type;
    const char *names[] = {"plain.bin", "inline.txt", "packed.bin", "link"};
    for (unsigned i = 0; i < 4; i++) if (strlen(names[i]) == len && memcmp(names[i], name, len) == 0) *mask |= 1U << i;
    return 0;
}
int main(int argc, char **argv) {
    struct disk d = {0}; struct apfs_nx nx = {0}; struct apfs_vol vol;
    struct apfs_dev dev = {0}; struct apfs_inode ino;
    uint64_t id; uint8_t type; unsigned mask = 0;
    CHECK(argc == 4);
    d.bytes = load(argv[1], &d.size); CHECK(d.bytes != NULL);
    dev.ctx = &d; dev.size = d.size; dev.read = read_disk;
    int error = apfs_nx_open(&nx, &dev);
    if (strcmp(argv[3], "bad-open") == 0) {
        CHECK(error != 0); CHECK(d.reads < 1050); apfs_nx_close(&nx); apfs_nx_close(&nx); free(d.bytes);
        puts("PASS malformed container rejected with bounded reads"); return 0;
    }
    CHECK(error == 0); CHECK(apfs_vol_open(&nx, 0, &vol) == 0);
    CHECK(apfs_inode_get(&vol, APFS_ROOT_DIR_INO_NUM, &ino) == 0);
    CHECK((ino.mode & APFS_S_IFMT) == APFS_S_IFDIR);
    CHECK(apfs_readdir(&vol, APFS_ROOT_DIR_INO_NUM, list_one, &mask) == 0 && mask == 15);
    const char *names[] = {"plain.bin", "inline.txt", "packed.bin"};
    for (unsigned i = 0; i < 3; i++) {
        char path[4096]; size_t size, got = 0; uint64_t logical;
        struct apfs_cfile cf = {0};
        snprintf(path, sizeof(path), "%s/%s", argv[2], names[i]);
        uint8_t *want = load(path, &size), *out = malloc(size + 32); CHECK(want && out);
        CHECK(apfs_lookup(&vol, APFS_ROOT_DIR_INO_NUM, names[i], strlen(names[i]), &id, &type) == 0);
        CHECK(type == APFS_DT_REG && apfs_inode_get(&vol, id, &ino) == 0);
        CHECK(apfs_inode_size(&vol, &ino, &logical) == 0 && logical == size);
        CHECK(apfs_read_file(&vol, &ino, &cf, 0, out, size + 32, &got) == 0);
        CHECK(got == size && memcmp(want, out, size) == 0);
        /* Unaligned partial reads, including resource-fork piece boundaries. */
        for (size_t off = 3; off < size; off += 32749) {
            size_t n = size - off > 4111 ? 4111 : size - off;
            CHECK(apfs_read_file(&vol, &ino, &cf, off, out, n, &got) == 0);
            CHECK(got == n && memcmp(want + off, out, n) == 0);
        }
        CHECK(apfs_read_file(&vol, &ino, &cf, size, out, 17, &got) == 0 && got == 0);
        apfs_cfile_fini(&cf); free(want); free(out);
    }
    CHECK(apfs_lookup(&vol, APFS_ROOT_DIR_INO_NUM, "missing", 7, &id, &type) == ENOENT);
    CHECK(apfs_lookup(&vol, APFS_ROOT_DIR_INO_NUM, "link", 4, &id, &type) == 0 && type == APFS_DT_LNK);
    char link[64]; size_t got;
    CHECK(apfs_readlink(&vol, id, link, sizeof(link), &got) == 0 && got == 10 && memcmp(link, "inline.txt", 10) == 0);
    apfs_nx_cache_flush(&nx); d.fail = true;
    CHECK(apfs_inode_get(&vol, APFS_ROOT_DIR_INO_NUM, &ino) != 0);
    apfs_nx_close(&nx); apfs_nx_close(&nx); free(d.bytes);
    puts("PASS metadata, directories, symlink, plain/zlib files, partial reads, EOF and device error");
    return 0;
}
