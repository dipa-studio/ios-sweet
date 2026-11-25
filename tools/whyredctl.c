/* Minimal Darwin diagnostics for the whyred SSH image. */
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <sys/sysctl.h>
#include <sys/utsname.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int failure(const char *what) { perror(what); return 1; }

static int output(const void *data, size_t length) {
    const char *p = data;
    while (length) {
        ssize_t n = write(STDOUT_FILENO, p, length);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return failure("write");
        p += n; length -= (size_t)n;
    }
    return 0;
}

static int cat_file(const char *path) {
    int fd = !strcmp(path, "-") ? STDIN_FILENO : open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) return failure(path);
    char data[16384]; int result = 0;
    for (;;) {
        ssize_t n = read(fd, data, sizeof(data));
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) { result = failure(path); break; }
        if (!n) break;
        if ((result = output(data, (size_t)n))) break;
    }
    if (fd != STDIN_FILENO) close(fd);
    return result;
}

static void print_stat(const char *name, const struct stat *s) {
    printf("%06o %u:%u %" PRId64 " bytes %" PRId64 " blocks %s\n",
        (unsigned)s->st_mode, (unsigned)s->st_uid, (unsigned)s->st_gid,
        (int64_t)s->st_size, (int64_t)s->st_blocks, name);
}

static int list_dir(const char *path) {
    DIR *dir = opendir(path);
    if (!dir) return failure(path);
    struct dirent *e; int result = 0;
    while ((e = readdir(dir))) {
        if (!strcmp(e->d_name, ".") || !strcmp(e->d_name, "..")) continue;
        struct stat s;
        if (fstatat(dirfd(dir), e->d_name, &s, AT_SYMLINK_NOFOLLOW)) { result = failure(e->d_name); continue; }
        print_stat(e->d_name, &s);
    }
    closedir(dir); return result;
}

static int disk_use(const char *path, unsigned depth, uint64_t *blocks) {
    if (depth > 64) { fprintf(stderr, "directory depth exceeds64: %s\n", path); return 1; }
    struct stat s;
    if (lstat(path, &s)) return failure(path);
    *blocks += (uint64_t)s.st_blocks;
    if (!S_ISDIR(s.st_mode)) return 0;
    DIR *dir = opendir(path);
    if (!dir) return failure(path);
    struct dirent *e; int result = 0;
    while ((e = readdir(dir))) {
        if (!strcmp(e->d_name, ".") || !strcmp(e->d_name, "..")) continue;
        char child[PATH_MAX];
        int n = snprintf(child, sizeof(child), "%s/%s", path, e->d_name);
        if (n < 0 || (size_t)n >= sizeof(child)) { result = 1; continue; }
        if (disk_use(child, depth + 1, blocks)) result = 1;
    }
    closedir(dir); return result;
}

static int processes(void) {
    int mib[] = { CTL_KERN, KERN_PROC, KERN_PROC_ALL, 0 };
    for (unsigned attempt = 0; attempt < 3; attempt++) {
        size_t size = 0;
        if (sysctl(mib, 4, NULL, &size, NULL, 0)) return failure("sysctl process size");
        if (size > 64 * 1024 * 1024) return 1;
        size += 32 * sizeof(struct kinfo_proc);
        struct kinfo_proc *rows = malloc(size);
        if (!rows) return failure("malloc");
        if (sysctl(mib, 4, rows, &size, NULL, 0)) {
            int saved = errno; free(rows); if (saved == ENOMEM) continue;
            errno = saved; return failure("sysctl processes");
        }
        puts("PID UID STATE NAME");
        for (size_t i = 0; i < size / sizeof(*rows); i++)
            printf("%d %u %d %.16s\n", rows[i].kp_proc.p_pid,
                (unsigned)rows[i].kp_eproc.e_ucred.cr_uid,
                (int)rows[i].kp_proc.p_stat, rows[i].kp_proc.p_comm);
        free(rows); return 0;
    }
    fprintf(stderr, "process list kept growing\n"); return 1;
}

int main(int argc, char **argv) {
    const char *command = argc > 1 ? argv[1] : "";
    const char *path = argc > 2 ? argv[2] : ".";
    if (!strcmp(command, "cat")) return cat_file(argc > 2 ? path : "-");
    if (!strcmp(command, "ls")) return list_dir(path);
    if (!strcmp(command, "ps")) return processes();
    if (!strcmp(command, "stat")) {
        struct stat s; if (lstat(path, &s)) return failure(path); print_stat(path, &s); return 0;
    }
    if (!strcmp(command, "fs")) {
        struct statfs s; if (statfs(path, &s)) return failure(path);
        printf("type=%s mount=%s block=%u total=%" PRIu64 " free=%" PRIu64 " available=%" PRIu64 "\n",
            s.f_fstypename, s.f_mntonname, (unsigned)s.f_bsize,
            (uint64_t)s.f_blocks, (uint64_t)s.f_bfree, (uint64_t)s.f_bavail);
        return 0;
    }
    if (!strcmp(command, "du")) {
        uint64_t blocks = 0; int result = disk_use(path, 0, &blocks);
        printf("%" PRIu64 " bytes allocated %s\n", blocks * 512, path); return result;
    }
    if (!strcmp(command, "uname")) {
        struct utsname s; if (uname(&s)) return failure("uname");
        printf("%s %s %s %s\n", s.sysname, s.nodename, s.release, s.machine); return 0;
    }
    if (!strcmp(command, "id")) { printf("uid=%u gid=%u euid=%u egid=%u\n",
        (unsigned)getuid(), (unsigned)getgid(), (unsigned)geteuid(), (unsigned)getegid()); return 0; }
    if (!strcmp(command, "readlink")) {
        char b[PATH_MAX]; ssize_t n = readlink(path, b, sizeof(b));
        if (n < 0) return failure(path);
        if (output(b, (size_t)n)) return 1;
        return output("\n", 1);
    }
    fprintf(stderr, "usage: whyredctl {ps|fs|du|ls|stat|cat|readlink|uname|id} [path]\n"); return 2;
}
