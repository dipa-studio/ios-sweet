/* Bounded read-only factory metadata export for a pinned whyred kernel.
 * Requires the corrected d_psize block-byte units (patch0178).
 * Opens only O_RDONLY; queries geometry and sends no SET or media-write ioctl.
 */
#include <TargetConditionals.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/sysctl.h>
#include <unistd.h>

#ifndef WHYRED_EXPECTED_UUID
#define WHYRED_EXPECTED_UUID "2ED4E8A4-6D1C-3C3C-980B-8533C25978D1"
#endif
#define EXPECTED_UUID WHYRED_EXPECTED_UUID
/* Read-only commands from this port's exact XNU bsd/sys/disk.h. */
#define DKIOCGETBLOCKSIZE _IOR('d', 24, uint32_t)
#define DKIOCGETBLOCKCOUNT _IOR('d', 25, uint64_t)
#define DKIOCISWRITABLE _IOR('d', 29, uint32_t)
#define PARTITION_BYTES (32u * 1024u * 1024u)
static int geometry_valid(uint32_t size, uint64_t count, uint32_t writable) {
    return size == 512 && count == PARTITION_BYTES / 512 && writable == 0;
}
#if defined(__aarch64__) && TARGET_OS_IPHONE
static int put_all(const unsigned char *data, size_t size) {
    while (size) {
        ssize_t n = write(STDOUT_FILENO, data, size);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return 1;
        data += n; size -= (size_t)n;
    }
    return 0;
}
#endif
static int read_persist(int full) {
#if !defined(__aarch64__) || !TARGET_OS_IPHONE
    (void)full;
    fprintf(stderr, "requires the physical iOS target\n"); return 1;
#else
    char uuid[80] = {0}; size_t length = sizeof(uuid) - 1;
    if (getuid() || sysctlbyname("kern.uuid", uuid, &length, NULL, 0) || strcmp(uuid, EXPECTED_UUID)) {
        fprintf(stderr, "root/pinned kernel guard failed\n"); return 1;
    }
    int fd = open("/dev/whyred-53-persist", O_RDONLY | O_CLOEXEC);
    if (fd < 0) { perror("persist open"); return 1; }
    uint32_t size = 0, writable = 1; uint64_t count = 0;
    int result = 1;
    if (ioctl(fd, DKIOCGETBLOCKSIZE, &size) || ioctl(fd, DKIOCGETBLOCKCOUNT, &count) ||
        ioctl(fd, DKIOCISWRITABLE, &writable) || !geometry_valid(size, count, writable)) {
        fprintf(stderr, "unexpected read-only geometry\n"); goto done;
    }
    unsigned char data[16384]; uint32_t remaining = full ? PARTITION_BYTES : sizeof(data);
    int first = 1; alarm(90);
    while (remaining) {
        size_t want = remaining < sizeof(data) ? remaining : sizeof(data);
        ssize_t n = read(fd, data, want);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0 || (size_t)n > want) { perror("persist read"); goto done; }
        if (first) {
            if (n < 1082 || data[1080] != 0x53 || data[1081] != 0xef) {
                fprintf(stderr, "expected ext filesystem superblock missing\n"); goto done;
            }
            first = 0;
        }
        if (put_all(data, (size_t)n)) { perror("export write"); goto done; }
        remaining -= (uint32_t)n;
    }
    fprintf(stderr, "factory export complete bytes=%u read_only=1 block_bytes=512\n",
        full ? PARTITION_BYTES : (unsigned)sizeof(data));
    result = 0;
done:
    alarm(0); close(fd); return result;
#endif
}
int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1], "self-test")) {
        if (!geometry_valid(512, 65536, 0) || geometry_valid(4096, 65536, 0) ||
            geometry_valid(512, 65535, 0) || geometry_valid(512, 65536, 1)) return 1;
        puts("PASS fixed read-only persist geometry and rejection cases"); return 0;
    }
    if (argc == 2 && !strcmp(argv[1], "probe")) return read_persist(0);
    if (argc == 2 && !strcmp(argv[1], "export")) return read_persist(1);
    fprintf(stderr, "usage: whyred-persist-read self-test | probe | export\n"); return 2;
}
