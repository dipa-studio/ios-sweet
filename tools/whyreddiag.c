/* Bounded diagnostics for a developer-owned whyred device.
 * Sampling is read-only; the explicit xattrs command uses one temporary file. */
#include <mach/mach.h>
#include <mach/thread_info.h>
#include <mach/vm_statistics.h>
#if defined(__aarch64__)
#include <mach/arm/thread_status.h>
#else
#include <mach/i386/thread_status.h>
#endif
#include <sys/resource.h>
#include <sys/sysctl.h>
#include <sys/xattr.h>
#include <sys/wait.h>
#include <mach-o/dyld_images.h>
#include <stddef.h>
#include <errno.h>
#include <grp.h>
#include <fcntl.h>
#include <inttypes.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static int memory_stats(void) {
    host_t host = mach_host_self();
    vm_statistics64_data_t vm;
    mach_msg_type_number_t count = HOST_VM_INFO64_COUNT;
    vm_size_t page_size = 0;
    kern_return_t kr = host_page_size(host, &page_size);
    if (kr == KERN_SUCCESS) kr = host_statistics64(host, HOST_VM_INFO64, (host_info64_t)&vm, &count);
    mach_port_deallocate(mach_task_self(), host);
    if (kr != KERN_SUCCESS) { fprintf(stderr, "host VM statistics: %d %s\n", kr, mach_error_string(kr)); return 1; }
    printf("VM page_size=%lu free=%u active=%u inactive=%u wired=%u compressor=%u internal=%u external=%u pageins=%llu pageouts=%llu swapins=%llu swapouts=%llu\n",
        (unsigned long)page_size, vm.free_count, vm.active_count, vm.inactive_count, vm.wire_count,
        vm.compressor_page_count, vm.internal_page_count, vm.external_page_count,
        (unsigned long long)vm.pageins, (unsigned long long)vm.pageouts,
        (unsigned long long)vm.swapins, (unsigned long long)vm.swapouts);
    return 0;
}

/* Receive queue metadata only: no message receive, port extraction or task stop. */
static int port_queues(pid_t pid) {
    task_t task = mach_task_self();
    kern_return_t kr;
    if (pid != getpid()) {
        kr = task_for_pid(mach_task_self(), pid, &task);
        if (kr != KERN_SUCCESS) { fprintf(stderr, "ports task_for_pid: %d\n", kr); return 1; }
    }
    mach_port_name_array_t names = NULL;
    mach_port_type_array_t types = NULL;
    mach_msg_type_number_t nn = 0, nt = 0;
    kr = mach_port_names(task, &names, &nn, &types, &nt);
    unsigned receivers = 0, sampled = 0, failures = 0, nonempty = 0;
    uint64_t messages = 0;
    int result = 1;
    if (kr == KERN_SUCCESS && nn == nt && nn <= 16384) {
        for (unsigned i = 0; i < nn; i++) {
            if (!(types[i] & MACH_PORT_TYPE_RECEIVE)) continue;
            receivers++;
            if (sampled + failures >= 512) continue;
            mach_port_status_t status = {0};
            mach_msg_type_number_t count = MACH_PORT_RECEIVE_STATUS_COUNT;
            kr = mach_port_get_attributes(task, names[i], MACH_PORT_RECEIVE_STATUS,
                (mach_port_info_t)&status, &count);
            if (kr != KERN_SUCCESS || count != MACH_PORT_RECEIVE_STATUS_COUNT) { failures++; continue; }
            sampled++; messages += status.mps_msgcount;
            if (status.mps_msgcount) {
                nonempty++;
                printf("PORTQ pid=%d name=0x%x messages=%u limit=%u seq=%u sets=%u flags=0x%x\n",
                    pid, names[i], status.mps_msgcount, status.mps_qlimit,
                    status.mps_seqno, status.mps_pset, status.mps_flags);
            }
        }
        result = sampled ? 0 : 1;
    }
    printf("PORTS pid=%d names=%u types=%u receivers=%u sampled=%u failures=%u nonempty=%u messages=%llu limited=%d read_only=1 drained=0\n",
        pid, nn, nt, receivers, sampled, failures, nonempty,
        (unsigned long long)messages, receivers > sampled + failures);
    if (names) vm_deallocate(mach_task_self(), (vm_address_t)names, (vm_size_t)nn * sizeof(*names));
    if (types) vm_deallocate(mach_task_self(), (vm_address_t)types, (vm_size_t)nt * sizeof(*types));
    if (pid != getpid()) mach_port_deallocate(mach_task_self(), task);
    return result;
}

static int queue_selftest(void) {
    mach_port_t port = MACH_PORT_NULL;
    kern_return_t kr = mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &port);
    if (kr != KERN_SUCCESS) return 1;
    int result = 1;
    kr = mach_port_insert_right(mach_task_self(), port, port, MACH_MSG_TYPE_MAKE_SEND);
    if (kr == KERN_SUCCESS) {
        mach_msg_header_t message = {0};
        message.msgh_bits = MACH_MSGH_BITS(MACH_MSG_TYPE_COPY_SEND, 0);
        message.msgh_size = sizeof(message); message.msgh_remote_port = port;
        message.msgh_id = 0x57515244;
        kr = mach_msg(&message, MACH_SEND_MSG | MACH_SEND_TIMEOUT, sizeof(message), 0,
            MACH_PORT_NULL, 1000, MACH_PORT_NULL);
        if (kr == KERN_SUCCESS && !port_queues(getpid())) {
            mach_port_status_t status = {0};
            mach_msg_type_number_t count = MACH_PORT_RECEIVE_STATUS_COUNT;
            kr = mach_port_get_attributes(mach_task_self(), port, MACH_PORT_RECEIVE_STATUS,
                (mach_port_info_t)&status, &count);
            if (kr == KERN_SUCCESS && count == MACH_PORT_RECEIVE_STATUS_COUNT && status.mps_msgcount == 1) {
                puts("PORTS selftest PASS own_message_preserved=1"); result = 0;
            }
        }
    }
    mach_port_mod_refs(mach_task_self(), port, MACH_PORT_RIGHT_RECEIVE, -1);
    mach_port_deallocate(mach_task_self(), port);
    return result;
}

static int sample(pid_t pid, int registers) {
    task_t task = MACH_PORT_NULL;
    kern_return_t kr;
    if (pid == getpid()) task = mach_task_self();
    else {
        kr = task_for_pid(mach_task_self(), pid, &task);
        if (kr != KERN_SUCCESS) {
            fprintf(stderr, "task_for_pid(%d): %d %s\n", pid, kr, mach_error_string(kr));
            return 1;
        }
    }
    thread_act_array_t threads = NULL;
    mach_msg_type_number_t count = 0;
    kr = task_threads(task, &threads, &count);
    if (kr != KERN_SUCCESS) {
        fprintf(stderr, "task_threads: %d %s\n", kr, mach_error_string(kr));
        if (pid != getpid()) mach_port_deallocate(mach_task_self(), task);
        return 1;
    }
    printf("pid=%d threads=%u live_sample=1 suspended=0\n", pid, count);
    unsigned sampled = 0;
    for (unsigned i = 0; i < count; i++) {
        if (i < 256) {
            thread_basic_info_data_t info;
            mach_msg_type_number_t n = THREAD_BASIC_INFO_COUNT;
            kr = thread_info(threads[i], THREAD_BASIC_INFO, (thread_info_t)&info, &n);
            printf("thread=%u info_kr=%d", i, kr);
            if (kr == KERN_SUCCESS) printf(" state=%d flags=%d suspend=%d user_us=%lld sys_us=%lld",
                info.run_state, info.flags, info.suspend_count,
                (long long)info.user_time.seconds * 1000000 + info.user_time.microseconds,
                (long long)info.system_time.seconds * 1000000 + info.system_time.microseconds);
            uint64_t pc = 0, sp = 0, fp = 0, lr = 0;
#if defined(__aarch64__)
            arm_thread_state64_t state;
            n = ARM_THREAD_STATE64_COUNT;
            kr = thread_get_state(threads[i], ARM_THREAD_STATE64, (thread_state_t)&state, &n);
            if (kr == KERN_SUCCESS) {
                pc = arm_thread_state64_get_pc(state); sp = arm_thread_state64_get_sp(state);
                fp = arm_thread_state64_get_fp(state); lr = arm_thread_state64_get_lr(state);
            }
#else
            x86_thread_state64_t state;
            n = x86_THREAD_STATE64_COUNT;
            kr = thread_get_state(threads[i], x86_THREAD_STATE64, (thread_state_t)&state, &n);
            if (kr == KERN_SUCCESS) { pc = state.__rip; sp = state.__rsp; fp = state.__rbp; }
#endif
            printf(" state_kr=%d pc=0x%" PRIx64 " sp=0x%" PRIx64 " fp=0x%" PRIx64 " lr=0x%" PRIx64, kr, pc, sp, fp, lr);
            if (registers && kr == KERN_SUCCESS) {
#if defined(__aarch64__)
                for (unsigned reg = 0; reg < 29; reg++)
                    printf(" x%u=0x%" PRIx64, reg, (uint64_t)state.__x[reg]);
#else
                printf(" registers_unsupported=1");
#endif
            }
            if (kr == KERN_SUCCESS) {
                sampled++;
                /* Unsuspended frames can change; bounds prevent loops and runaway reads. */
                uint64_t start = sp;
                for (unsigned j = 0; j < 24 && fp >= start && fp - start < 8 * 1024 * 1024 && !(fp & 7); j++) {
                    uint64_t frame[2]; vm_size_t got = 0;
                    kr = vm_read_overwrite(task, (vm_address_t)fp, sizeof(frame), (vm_address_t)frame, &got);
                    if (kr != KERN_SUCCESS || got != sizeof(frame)) break;
                    printf(" bt%u=0x%" PRIx64, j, frame[1]);
                    if (frame[0] <= fp) break;
                    fp = frame[0];
                }
            }
            putchar('\n');
        }
        mach_port_deallocate(mach_task_self(), threads[i]);
    }
    if (threads) vm_deallocate(mach_task_self(), (vm_address_t)threads, count * sizeof(*threads));
    if (pid != getpid()) mach_port_deallocate(mach_task_self(), task);
    return sampled ? 0 : 1;
}

static int region_read(pid_t pid, uint64_t address, size_t length) {
    if (!address || !length || length > 4096 || address > UINT64_MAX - length) return 2;
    task_t task = MACH_PORT_NULL;
    kern_return_t kr = task_for_pid(mach_task_self(), pid, &task);
    if (kr) { fprintf(stderr, "region task_for_pid: %d\n", kr); return 1; }
    unsigned char bytes[4096]; vm_size_t got = 0;
    kr = vm_read_overwrite(task, (vm_address_t)address, length, (vm_address_t)bytes, &got);
    mach_port_deallocate(mach_task_self(), task);
    printf("WHYRED DIAG: region pid=%d address=0x%llx bytes=%lu kr=%d read_only=1\n",
           pid, (unsigned long long)address, (unsigned long)got, kr);
    if (kr || got != length) return 1;
    for (size_t i = 0; i < length; i++) printf("%02x%s", bytes[i], (i + 1) % 16 ? "" : "\n");
    if (length % 16) putchar('\n');
    return 0;
}

static int task_cache(pid_t pid) {
    task_t task = MACH_PORT_NULL;
    kern_return_t kr = task_for_pid(mach_task_self(), pid, &task);
    if (kr) { fprintf(stderr, "cache task_for_pid: %d\n", kr); return 1; }
    task_dyld_info_data_t info = {0}; mach_msg_type_number_t count = TASK_DYLD_INFO_COUNT;
    kr = task_info(task, TASK_DYLD_INFO, (task_info_t)&info, &count);
    uintptr_t slide = 0; vm_size_t got = 0;
    if (!kr && info.all_image_info_format == TASK_DYLD_ALL_IMAGE_INFO_64) {
        kr = vm_read_overwrite(task, info.all_image_info_addr +
            offsetof(struct dyld_all_image_infos, sharedCacheSlide), sizeof(slide),
            (vm_address_t)&slide, &got);
    } else if (!kr) kr = KERN_INVALID_ARGUMENT;
    mach_port_deallocate(mach_task_self(), task);
    printf("WHYRED DIAG: cache pid=%d kr=%d bytes=%lu slide=0x%llx read_only=1\n",
           pid, kr, (unsigned long)got, (unsigned long long)slide);
    return kr || got != sizeof(slide) ? 1 : 0;
}

static double now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) { perror("clock_gettime"); exit(1); }
    return t.tv_sec + t.tv_nsec / 1e9;
}

static int kernel_info(void) {
    char uuid[128] = {0}; size_t size = sizeof(uuid) - 1;
    if (sysctlbyname("kern.uuid", uuid, &size, NULL, 0)) { perror("kern.uuid"); return 1; }
    uuid[sizeof(uuid) - 1] = 0;
    printf("WHYRED DIAG: kernel_uuid=%s\n", uuid);
    return 0;
}

static int session_info(void) {
    host_t host = mach_host_self();
    uint32_t flags = 0, multiuser = 0;
    /* The iOS libsyscall getters read the same commpage used by usermanagerd.
     * No host-privileged setter or guessed memory address is needed. */
    kern_return_t flags_kr = host_get_multiuser_config_flags(host, &flags);
    kern_return_t mode_kr = host_check_multiuser_mode(host, &multiuser);
    mach_port_deallocate(mach_task_self(), host);
    printf("WHYRED DIAG: session flags_kr=%d mode_kr=%d flags=0x%08" PRIx32
           " multiuser=%" PRIu32 " read_only=1\n", flags_kr, mode_kr, flags, multiuser);
    return flags_kr == KERN_SUCCESS && mode_kr == KERN_SUCCESS ? 0 : 1;
}

static int xattr_probe(const char *directory) {
    char path[1024];
    if (directory[0] != '/' || snprintf(path, sizeof(path), "%s/whyred-xattrs.XXXXXX", directory) >= (int)sizeof(path)) return 2;
    int fd = mkstemp(path);
    if (fd < 0) { perror("xattrs mkstemp"); return 1; }
    int result = 1; unsigned checks = 0;
    const char *name = "user.whyred.snapshot";
    unsigned char bytes[16384], got[16384]; char names[4096];
    const size_t sizes[] = {0, 1, 68, 511, 4096, 16384, 68, 1, 0};
#define XCHECK(condition) do { checks++; if (!(condition)) { \
    fprintf(stderr, "WHYRED DIAG: xattrs check=%u failed line=%d errno=%d\n", checks, __LINE__, errno); goto cleanup; } } while (0)
    for (unsigned i = 0; i < sizeof(sizes) / sizeof(sizes[0]); i++) {
        size_t size = sizes[i];
        for (size_t j = 0; j < size; j++) bytes[j] = (unsigned char)(j * 17 + i);
        XCHECK(fsetxattr(fd, name, bytes, size, 0, 0) == 0);
        XCHECK(fgetxattr(fd, name, NULL, 0, 0, 0) == (ssize_t)size);
        memset(got, 0x7e, sizeof(got));
        if (size > 1) {
            errno = 0;
            XCHECK(fgetxattr(fd, name, got, size - 1, 0, 0) == -1 && errno == ERANGE);
            XCHECK(got[0] == 0x7e);
        }
        XCHECK(fgetxattr(fd, name, got, sizeof(got), 0, 0) == (ssize_t)size);
        XCHECK(memcmp(bytes, got, size) == 0);
        ssize_t count = flistxattr(fd, names, sizeof(names), 0);
        XCHECK(count > 0 && count <= (ssize_t)sizeof(names));
        int found = 0;
        for (size_t at = 0; at < (size_t)count;) {
            size_t length = strnlen(names + at, (size_t)count - at);
            XCHECK(length < (size_t)count - at);
            if (!strcmp(names + at, name)) found = 1;
            at += length + 1;
        }
        XCHECK(found);
    }
    XCHECK(fremovexattr(fd, name, 0) == 0);
    errno = 0;
    XCHECK(fgetxattr(fd, name, got, sizeof(got), 0, 0) == -1 && errno == ENOATTR);
    printf("WHYRED DIAG: xattrs PASS checks=%u max_bytes=%zu temporary_file=1\n", checks, sizeof(bytes));
    result = 0;
cleanup:
    if (close(fd)) { perror("xattrs close"); result = 1; }
    if (unlink(path)) { perror("xattrs cleanup"); result = 1; }
#undef XCHECK
    return result;
}

static int run_mobile(char **args, unsigned seconds) {
    if (getuid() || args[0][0] != '/') { fprintf(stderr, "run-mobile requires root and an absolute executable\n"); return 2; }
    pid_t child = fork();
    if (child < 0) { perror("fork"); return 1; }
    if (!child) {
        if (setpgid(0, 0) || initgroups("mobile", 501) || setgid(501) || setuid(501)) { perror("mobile credentials"); _exit(126); }
        struct rlimit no_core = {0, 0};
        if (setrlimit(RLIMIT_CORE, &no_core)) { perror("setrlimit"); _exit(126); }
        if (setenv("HOME", "/var/mobile", 1) || setenv("USER", "mobile", 1) || setenv("LOGNAME", "mobile", 1) || chdir("/var/mobile")) { perror("mobile environment"); _exit(126); }
        execv(args[0], args); perror("execv"); _exit(127);
    }
    double deadline = now() + seconds;
    int timed_out = 0, killed = 0, status;
    for (;;) {
        pid_t got = waitpid(child, &status, WNOHANG);
        if (got == child) break;
        if (got < 0 && errno != EINTR) { perror("waitpid"); return 1; }
        double t = now();
        if (!timed_out && t >= deadline) { kill(-child, SIGTERM); timed_out = 1; }
        if (timed_out && !killed && t >= deadline + 2) { kill(-child, SIGKILL); killed = 1; }
        struct timespec delay = {0, 100000000}; nanosleep(&delay, NULL);
    }
    fprintf(stderr, "WHYRED DIAG: child_status=0x%x exit=%d signal=%d timeout=%d\n", status,
        WIFEXITED(status) ? WEXITSTATUS(status) : -1, WIFSIGNALED(status) ? WTERMSIG(status) : 0, timed_out);
    return timed_out ? 124 : WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}

int main(int argc, char **argv) {
    if ((argc == 3 && (!strcmp(argv[1], "cache") || !strcmp(argv[1], "ports"))) ||
        (argc == 5 && !strcmp(argv[1], "region"))) {
        char *end; errno = 0; long pid = strtol(argv[2], &end, 10);
        if (errno || *end || pid <= 0 || pid > 0x7fffffff) return 2;
        if (argc == 3) return !strcmp(argv[1], "ports") ? port_queues((pid_t)pid) : task_cache((pid_t)pid);
        if (argv[3][0] == '-' || argv[4][0] == '-') return 2;
        errno = 0; uint64_t address = strtoull(argv[3], &end, 0);
        if (errno || *end) return 2;
        errno = 0; unsigned long length = strtoul(argv[4], &end, 0);
        if (errno || *end || !length || length > 4096) return 2;
        return region_read((pid_t)pid, address, length);
    }
    if (argc == 2 && !strcmp(argv[1], "kernel")) return kernel_info();
    if (argc == 2 && !strcmp(argv[1], "session")) return session_info();
    if (argc == 3 && !strcmp(argv[1], "xattrs")) return xattr_probe(argv[2]);
    if (argc == 2 && !strcmp(argv[1], "memory")) return memory_stats();
    if (argc == 2 && !strcmp(argv[1], "selftest")) {
        static const unsigned char probe[] = {0x13,0x37,0x42,0x19,0x88,0x76,0x54,0x32};
        return queue_selftest() || memory_stats() || sample(getpid(), 0) || task_cache(getpid()) ||
            region_read(getpid(), (uintptr_t)probe, sizeof(probe));
    }
    if (argc == 3 && (!strcmp(argv[1], "threads") || !strcmp(argv[1], "registers"))) {
        char *end; errno = 0; long pid = strtol(argv[2], &end, 10);
        if (errno || *end || pid <= 0 || pid > 0x7fffffff) return 2;
        return sample((pid_t)pid, !strcmp(argv[1], "registers"));
    }
    if (argc >= 3 && !strcmp(argv[1], "run-mobile")) return run_mobile(argv + 2, 30);
    /* The finite40s display pilot may finish its final45s bounded capture.
     * Keep the old general runner at30s; never extend continuous live mode. */
    if (argc == 4 && !strcmp(argv[1], "run-mobile-display") && !strcmp(argv[3], "live-window"))
        return run_mobile(argv + 2, 90);
    fprintf(stderr, "usage: whyreddiag selftest | memory | kernel | session | cache PID | ports PID | region PID ADDRESS LENGTH(1..4096) | xattrs /temporary-directory | threads PID | registers PID | run-mobile /executable [args] | run-mobile-display /executable live-window\n"); return 2;
}
