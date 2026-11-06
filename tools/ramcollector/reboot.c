/* RAM collector automatic return; reboot syscall, no block devices or MMIO. */
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    if (argc != 2 || strcmp(argv[1], "--recovery") != 0) {
        fputs("usage: collector-reboot --recovery\n", stderr);
        return 64;
    }
    /* RESTART2 runs kernel reboot notifiers, including syscon-reboot-mode. */
    if (syscall(SYS_reboot, 0xfee1dead, 672274793, 0xa1b2c3d4, "recovery") < 0) {
        perror("reboot recovery");
        return errno ? errno : 1;
    }
    return 0;
}
