/* Read-only System95 -> display overlay comparison using the preserved APFS
 * reader, independently of the Python image writer. No device access. */
#include "apfs_lib.h"

struct disk { FILE *f; uint64_t size; struct apfs_dev dev; struct apfs_nx nx; struct apfs_vol vol; };
struct entry { char *name; uint64_t id; uint8_t type; };
struct listing { struct entry *v; size_t n; };
static struct disk disks[2];
static unsigned nodes, files, dirs, links, changed, added;
static int display_memory_policy, minimal_hardware;
static const char *hardware_paths[] = {
    "/System/Library/LaunchDaemons/com.apple.wifi.hostapd.plist",
    "/System/Library/LaunchDaemons/com.apple.wifi.wapic.plist",
    "/System/Library/LaunchDaemons/com.apple.wifiFirmwareLoader.plist",
    "/System/Library/LaunchDaemons/com.apple.wifianalyticsd.plist",
    "/System/Library/LaunchDaemons/com.apple.wifid.plist",
    "/System/Library/LaunchDaemons/com.apple.wifip2pd.plist",
    "/System/Library/LaunchDaemons/com.apple.wifivelocityd.plist",
    "/System/Library/LaunchDaemons/com.apple.bluetoothuiservice.plist",
    "/System/Library/LaunchDaemons/com.apple.bluetoothuserd.plist",
    "/System/Library/LaunchDaemons/com.apple.WirelessRadioManager.plist",
    "/System/Library/LaunchDaemons/com.apple.nfcd.plist",
    "/System/Library/LaunchDaemons/com.apple.applecamerad.plist",
    "/System/Library/LaunchDaemons/com.apple.dietapplecamerad.plist",
    "/System/Library/LaunchDaemons/com.apple.dietappleh13camerad.plist",
    "/System/Library/LaunchDaemons/com.apple.ptpcamerad.plist",
    "/System/Library/LaunchDaemons/com.apple.gpsd.plist",
    "/System/Library/LaunchDaemons/com.apple.awdd.plist",
    "/System/Library/LaunchDaemons/com.apple.accessibility.motiontrackingd.plist",
    "/System/Library/LaunchDaemons/com.apple.DumpBasebandCrash.plist",
};
static int hardware_exception(const char *path) {
    if (!minimal_hardware) return 0;
    for (unsigned i = 0; i < sizeof(hardware_paths) / sizeof(*hardware_paths); i++)
        if (!strcmp(path, hardware_paths[i])) return 1;
    return 0;
}
static uint64_t bytes;
static unsigned char buffers[2][1024 * 1024];

static int rd(void *ctx, uint64_t off, void *data, size_t count) {
    struct disk *d = ctx;
    if (off > d->size || count > d->size - off || off > INT64_MAX ||
        fseeko(d->f, (off_t)off, SEEK_SET) || fread(data, 1, count, d->f) != count) return EIO;
    return 0;
}
static int collect(void *ctx, const char *name, size_t len, uint64_t id, uint8_t type) {
    struct listing *ls = ctx;
    if ((len == 1 && name[0] == '.') || (len == 2 && !memcmp(name, "..", 2))) return 0;
    if (!len || len > 255 || memchr(name, '/', len) || memchr(name, 0, len) || ls->n >= 100000) return EINVAL;
    struct entry *v = realloc(ls->v, (ls->n + 1) * sizeof(*v));
    if (!v) return ENOMEM;
    ls->v = v;
    char *p = malloc(len + 1);
    if (!p) return ENOMEM;
    memcpy(p, name, len); p[len] = 0;
    ls->v[ls->n++] = (struct entry){p, id, type};
    return 0;
}
static int order(const void *a, const void *b) {
    return strcmp(((const struct entry *)a)->name, ((const struct entry *)b)->name);
}
static int child_path(char *out, size_t cap, const char *parent, const char *name) {
    int n = snprintf(out, cap, "%s%s%s", parent, strcmp(parent, "/") ? "/" : "", name);
    return n < 0 || (size_t)n >= cap ? EINVAL : 0;
}
static unsigned added_mode(const char *path) {
    if (!strcmp(path, "/usr/local/whyred/bin/whyred-display") ||
        !strcmp(path, "/usr/local/whyred/bin/whyred-display-wake")) return 0100755;
    if (!strcmp(path, "/System/Library/LaunchDaemons/org.whyred.display.plist")) return 0100644;
    return 0;
}
static unsigned parent_delta(const char *path) {
    if (!strcmp(path, "/usr/local/whyred/bin")) return 2;
    if (!strcmp(path, "/System/Library/LaunchDaemons")) return 1;
    return 0;
}
static int new_file(const struct entry *entry, const char *path) {
    struct apfs_inode in;
    unsigned mode = added_mode(path);
    int e = apfs_inode_get(&disks[1].vol, entry->id, &in);
    if (e) return e;
    /* The writer may store a new regular file compressed (UF_COMPRESSED0x20).
     * Preserve strict flag equality for old files; no other new BSD flags. */
    if (!mode || entry->type != 8 || in.mode != mode || in.owner || in.group ||
        (in.bsd_flags & ~0x20u)) return EINVAL;
    added++;
    return 0; /* Python separately compares all new bytes and metadata. */
}
static int walk(uint64_t a, uint64_t b, const char *path, unsigned depth) {
    if (depth > 128 || ++nodes > 100000) return EINVAL;
    struct apfs_inode in[2];
    int e = apfs_inode_get(&disks[0].vol, a, &in[0]);
    if (!e) e = apfs_inode_get(&disks[1].vol, b, &in[1]);
    if (e) return e;
    unsigned delta = parent_delta(path);
    if (in[0].mode != in[1].mode || in[0].owner != in[1].owner || in[0].group != in[1].group ||
        in[0].bsd_flags != in[1].bsd_flags || in[0].nchildren < 0 ||
        (uint64_t)in[0].nchildren + delta != (uint64_t)in[1].nchildren ||
        in[0].create_time != in[1].create_time || in[0].mod_time != in[1].mod_time ||
        in[0].change_time != in[1].change_time || in[0].access_time != in[1].access_time) e = EINVAL;
    unsigned kind = in[0].mode & 0170000;
    if (!e && kind == 0040000) {
        dirs++;
        struct listing ls[2] = {{0}};
        e = apfs_readdir(&disks[0].vol, a, collect, &ls[0]);
        if (!e) e = apfs_readdir(&disks[1].vol, b, collect, &ls[1]);
        if (!e && ls[0].n + delta != ls[1].n) e = EINVAL;
        for (unsigned j = 0; j < 2; j++) {
            qsort(ls[j].v, ls[j].n, sizeof(struct entry), order);
            for (size_t i = 1; !e && i < ls[j].n; i++)
                if (!strcmp(ls[j].v[i - 1].name, ls[j].v[i].name)) e = EINVAL;
        }
        size_t i = 0, j = 0;
        while (!e && (i < ls[0].n || j < ls[1].n)) {
            int cmp = i == ls[0].n ? 1 : j == ls[1].n ? -1 : strcmp(ls[0].v[i].name, ls[1].v[j].name);
            char child[4096];
            if (cmp < 0) { e = EINVAL; break; } /* Deletion forbidden. */
            e = child_path(child, sizeof(child), path, ls[1].v[j].name);
            if (e) break;
            if (cmp > 0) { e = new_file(&ls[1].v[j++], child); continue; }
            if (ls[0].v[i].type != ls[1].v[j].type) { e = EINVAL; break; }
            e = walk(ls[0].v[i++].id, ls[1].v[j++].id, child, depth + 1);
        }
        for (unsigned k = 0; k < 2; k++) {
            for (size_t n = 0; n < ls[k].n; n++) free(ls[k].v[n].name);
            free(ls[k].v);
        }
    } else if (!e && kind == 0120000) {
        links++; char buf[2][4096]; size_t n[2] = {0};
        e = apfs_readlink(&disks[0].vol, a, buf[0], sizeof(buf[0]), &n[0]);
        if (!e) e = apfs_readlink(&disks[1].vol, b, buf[1], sizeof(buf[1]), &n[1]);
        if (!e && (n[0] != n[1] || memcmp(buf[0], buf[1], n[0]))) e = EINVAL;
    } else if (!e && kind == 0100000) {
        files++; uint64_t size[2] = {0};
        e = apfs_inode_size(&disks[0].vol, &in[0], &size[0]);
        if (!e) e = apfs_inode_size(&disks[1].vol, &in[1], &size[1]);
        if (!e && (hardware_exception(path) || !strcmp(path, "/System/Library/xpc/launchd.plist") ||
            (display_memory_policy && !strcmp(path,
             "/System/Library/LaunchDaemons/com.apple.jetsamproperties.D22.plist")))) {
            changed++; return 0; /* Builder separately compares bytes and the full policy dictionary. */
        }
        if (!e && size[0] != size[1]) e = EINVAL;
        struct apfs_cfile cf[2] = {{0}};
        for (uint64_t off = 0; !e && off < size[0]; off += sizeof(buffers[0])) {
            size_t count = size[0] - off < sizeof(buffers[0]) ? (size_t)(size[0] - off) : sizeof(buffers[0]);
            size_t got[2] = {0};
            for (unsigned k = 0; !e && k < 2; k++)
                e = apfs_read_file(&disks[k].vol, &in[k], &cf[k], off, buffers[k], count, &got[k]);
            if (!e && (got[0] != count || got[1] != count || memcmp(buffers[0], buffers[1], count))) e = EIO;
            if (!e) bytes += count;
        }
        apfs_cfile_fini(&cf[0]); apfs_cfile_fini(&cf[1]);
    } else if (!e) e = EINVAL;
    if (e) fprintf(stderr, "comparison failure=%d path=%s\n", e, path);
    if (nodes % 5000 == 0) fprintf(stderr, "nodes=%u files=%u bytes=%llu\n", nodes, files, (unsigned long long)bytes);
    return e;
}
int main(int argc, char **argv) {
    if (argc < 3 || argc > 5) return 2;
    for (int i = 3; i < argc; i++) {
        if (!strcmp(argv[i], "--display-memory-policy") && !display_memory_policy) display_memory_policy = 1;
        else if (!strcmp(argv[i], "--minimal-hardware") && !minimal_hardware) minimal_hardware = 1;
        else return 2;
    }
    if (minimal_hardware && !display_memory_policy) return 2;
    for (unsigned i = 0; i < 2; i++) {
        struct disk *d = &disks[i];
        d->f = fopen(argv[i + 1], "rb");
        if (!d->f || fseeko(d->f, 0, SEEK_END)) return 2;
        off_t size = ftello(d->f);
        if (size < 0) return 2;
        d->size = (uint64_t)size;
        d->dev.ctx = d; d->dev.size = d->size; d->dev.read = rd;
        int e = apfs_nx_open(&d->nx, &d->dev);
        if (!e) e = apfs_vol_open(&d->nx, 0, &d->vol);
        if (e) return 3;
    }
    int e = walk(APFS_ROOT_DIR_INO_NUM, APFS_ROOT_DIR_INO_NUM, "/", 0);
    if (!e && (changed != 1u + (unsigned)display_memory_policy +
            (minimal_hardware ? sizeof(hardware_paths) / sizeof(*hardware_paths) : 0u) || added != 3)) e = EINVAL;
    printf("{\"passed\":%s,\"nodes\":%u,\"files\":%u,\"directories\":%u,\"symlinks\":%u,"
           "\"exact_bytes_compared\":%llu,\"explicit_file_exceptions\":%u,\"added_files\":%u}\n",
           e ? "false" : "true", nodes, files, dirs, links, (unsigned long long)bytes, changed, added);
    for (unsigned i = 0; i < 2; i++) { apfs_nx_close(&disks[i].nx); fclose(disks[i].f); }
    return e ? 1 : 0;
}
