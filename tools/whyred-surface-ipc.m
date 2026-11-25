/* Own-surface IPC diagnostic; no display, daemon, or filesystem changes. */
#import <Foundation/Foundation.h>
#if __has_include(<IOSurface/IOSurface.h>) && !defined(WHYRED_PROBE_IOSURFACE_DECLS)
#import <IOSurface/IOSurface.h>
#else
typedef struct __IOSurface *IOSurfaceRef;
extern const CFStringRef kIOSurfaceWidth, kIOSurfaceHeight, kIOSurfaceBytesPerElement;
extern const CFStringRef kIOSurfaceBytesPerRow, kIOSurfaceAllocSize, kIOSurfacePixelFormat;
extern IOSurfaceRef IOSurfaceCreate(CFDictionaryRef);
extern IOSurfaceRef IOSurfaceLookupFromMachPort(mach_port_t);
extern mach_port_t IOSurfaceCreateMachPort(IOSurfaceRef);
extern kern_return_t IOSurfaceLock(IOSurfaceRef, uint32_t, uint32_t *);
extern kern_return_t IOSurfaceUnlock(IOSurfaceRef, uint32_t, uint32_t *);
extern void *IOSurfaceGetBaseAddress(IOSurfaceRef);
extern size_t IOSurfaceGetWidth(IOSurfaceRef), IOSurfaceGetHeight(IOSurfaceRef);
extern size_t IOSurfaceGetBytesPerRow(IOSurfaceRef);
#endif
#include <mach/mach.h>
#include <mach/task_special_ports.h>
#include <spawn.h>
#include <sys/wait.h>
#include <signal.h>
#include <unistd.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
extern char **environ;
/* Exact declaration from xnu libsyscall/wrappers/spawn/spawn_private.h. */
extern int posix_spawnattr_set_registered_ports_np(posix_spawnattr_t *, mach_port_t [], uint32_t);

enum { WIDTH = 8, HEIGHT = 8, STRIDE = 64, BYTES = HEIGHT * STRIDE, REQUEST = 710, REPLY = 711 };
struct transfer {
    mach_msg_header_t head;
    mach_msg_body_t body;
    mach_msg_port_descriptor_t surface;
};
union receive_buffer {
    struct transfer transfer;
    char bytes[sizeof(struct transfer) + MAX_TRAILER_SIZE];
};

static void drop(mach_port_t p) {
    if (MACH_PORT_VALID(p)) mach_port_deallocate(mach_task_self(), p);
}
static int pattern(IOSurfaceRef s, unsigned before, unsigned after) {
    if (IOSurfaceGetWidth(s) != WIDTH || IOSurfaceGetHeight(s) != HEIGHT ||
        IOSurfaceGetBytesPerRow(s) != STRIDE || IOSurfaceLock(s, 0, NULL)) return 1;
    unsigned char *p = IOSurfaceGetBaseAddress(s);
    int failed = p == NULL;
    for (unsigned i = 0; p && i < BYTES; i++) failed |= p[i] != (unsigned char)(i ^ before);
    if (!failed) for (unsigned i = 0; i < BYTES; i++) p[i] = (unsigned char)(i ^ after);
    return IOSurfaceUnlock(s, 0, NULL) || failed;
}

static int child(void) {
    /* One child-only registered port; real bootstrap/service access is intact. */
    mach_port_array_t ports = NULL;
    mach_msg_type_number_t count = 0;
    mach_port_t channel = MACH_PORT_NULL, reply = MACH_PORT_NULL;
    if (mach_ports_lookup(mach_task_self(), &ports, &count)) return 2;
    printf("WHYRED SURFACE IPC: child registered_ports=%u\n", count);
    if (count >= 1 && MACH_PORT_VALID(ports[0])) {
        channel = ports[0];
        for (unsigned i = 1; i < count; i++) drop(ports[i]);
    }
    else for (unsigned i = 0; i < count; i++) drop(ports[i]);
    if (ports) vm_deallocate(mach_task_self(), (vm_address_t)ports, count * sizeof(*ports));
    if (!MACH_PORT_VALID(channel) ||
        mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &reply)) return 2;
    mach_msg_header_t request = {0};
    request.msgh_bits = MACH_MSGH_BITS(MACH_MSG_TYPE_COPY_SEND, MACH_MSG_TYPE_MAKE_SEND_ONCE);
    request.msgh_size = sizeof(request); request.msgh_remote_port = channel;
    request.msgh_local_port = reply; request.msgh_id = REQUEST;
    if (mach_msg(&request, MACH_SEND_MSG | MACH_SEND_TIMEOUT, sizeof(request), 0,
                 MACH_PORT_NULL, 5000, MACH_PORT_NULL)) return 2;
    union receive_buffer buf = {0};
    if (mach_msg(&buf.transfer.head, MACH_RCV_MSG | MACH_RCV_TIMEOUT, 0, sizeof(buf),
                 reply, 5000, MACH_PORT_NULL)) return 2;
    struct transfer *m = &buf.transfer;
    if (m->head.msgh_id != REPLY || m->head.msgh_size != sizeof(*m) ||
        !(m->head.msgh_bits & MACH_MSGH_BITS_COMPLEX) || m->body.msgh_descriptor_count != 1 ||
        m->surface.type != MACH_MSG_PORT_DESCRIPTOR) {
        mach_msg_destroy(&m->head); return 2;
    }
    drop(channel);
    mach_port_mod_refs(mach_task_self(), reply, MACH_PORT_RIGHT_RECEIVE, -1);
    IOSurfaceRef s = IOSurfaceLookupFromMachPort(m->surface.name);
    int result = !s || pattern(s, 0x31, 0x6d);
    if (s) CFRelease(s);
    drop(m->surface.name);
    printf("WHYRED SURFACE IPC: child lookup=%d initial_pixels=%s\n", s != NULL, result ? "FAIL" : "PASS");
    return result;
}

static int parent(const char *executable) {
    int result = 1, status = 0;
    const char *stage = "create";
    pid_t pid = -1;
    mach_port_t channel = MACH_PORT_NULL, surface_port = MACH_PORT_NULL;
    IOSurfaceRef s = NULL;
    posix_spawnattr_t attr;
    if (posix_spawnattr_init(&attr)) return 1;
    NSDictionary *properties = @{
        (__bridge NSString *)kIOSurfaceWidth: @(WIDTH), (__bridge NSString *)kIOSurfaceHeight: @(HEIGHT),
        (__bridge NSString *)kIOSurfaceBytesPerElement: @4, (__bridge NSString *)kIOSurfaceBytesPerRow: @(STRIDE),
        (__bridge NSString *)kIOSurfaceAllocSize: @(BYTES), (__bridge NSString *)kIOSurfacePixelFormat: @(0x42475241u)
    };
    s = IOSurfaceCreate((__bridge CFDictionaryRef)properties);
    if (!s || IOSurfaceGetWidth(s) != WIDTH || IOSurfaceGetHeight(s) != HEIGHT ||
        IOSurfaceGetBytesPerRow(s) != STRIDE || IOSurfaceLock(s, 0, NULL)) goto done;
    {
        unsigned char *p = IOSurfaceGetBaseAddress(s);
        if (p) for (unsigned i = 0; i < BYTES; i++) p[i] = (unsigned char)(i ^ 0x31);
        int unlocked = IOSurfaceUnlock(s, 0, NULL);
        if (!p || unlocked) goto done;
    }
    stage = "port";
    surface_port = IOSurfaceCreateMachPort(s);
    if (!MACH_PORT_VALID(surface_port) ||
        mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &channel) ||
        mach_port_insert_right(mach_task_self(), channel, channel, MACH_MSG_TYPE_MAKE_SEND) ||
        posix_spawnattr_set_registered_ports_np(&attr, &channel, 1)) goto done;
    {
        char *args[] = {(char *)executable, "--child", NULL};
        stage = "spawn";
        int spawn_error = posix_spawn(&pid, executable, NULL, &attr, args, environ);
        if (spawn_error) { printf("WHYRED SURFACE IPC: spawn_error=%d\n", spawn_error); goto done; }
        stage = "receive";
        union receive_buffer buf = {0};
        if (mach_msg(&buf.transfer.head, MACH_RCV_MSG | MACH_RCV_TIMEOUT, 0, sizeof(buf),
                     channel, 5000, MACH_PORT_NULL)) goto done;
        mach_msg_header_t *request = &buf.transfer.head;
        if (request->msgh_id != REQUEST || request->msgh_size != sizeof(*request) ||
            (request->msgh_bits & MACH_MSGH_BITS_COMPLEX) || !MACH_PORT_VALID(request->msgh_remote_port)) {
            mach_msg_destroy(request); goto done;
        }
        struct transfer msg = {0};
        msg.head.msgh_bits = MACH_MSGH_BITS(MACH_MSG_TYPE_MOVE_SEND_ONCE, 0) | MACH_MSGH_BITS_COMPLEX;
        msg.head.msgh_remote_port = request->msgh_remote_port;
        msg.head.msgh_size = sizeof(msg); msg.head.msgh_id = REPLY;
        msg.body.msgh_descriptor_count = 1;
        msg.surface.name = surface_port; msg.surface.disposition = MACH_MSG_TYPE_COPY_SEND;
        msg.surface.type = MACH_MSG_PORT_DESCRIPTOR;
        if (mach_msg(&msg.head, MACH_SEND_MSG | MACH_SEND_TIMEOUT, sizeof(msg), 0,
                     MACH_PORT_NULL, 5000, MACH_PORT_NULL)) { drop(request->msgh_remote_port); goto done; }
        stage = "child-exit";
        for (unsigned i = 0; i < 100; i++) {
            pid_t waited = waitpid(pid, &status, WNOHANG);
            if (waited == pid) { pid = -1; break; }
            if (waited < 0 && errno != EINTR) goto done;
            usleep(100000);
        }
        if (pid > 0 || !WIFEXITED(status) || WEXITSTATUS(status)) goto done;
        stage = "verify";
        result = pattern(s, 0x6d, 0x31);
    }
done:
    if (pid > 0) { kill(pid, SIGKILL); while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {} }
    posix_spawnattr_destroy(&attr);
    if (MACH_PORT_VALID(channel)) {
        drop(channel);
        mach_port_mod_refs(mach_task_self(), channel, MACH_PORT_RIGHT_RECEIVE, -1);
    }
    drop(surface_port);
    if (s) CFRelease(s);
    printf("WHYRED SURFACE IPC: parent shared_pixels=%s bytes=%u stage=%s display_changed=0\n", result ? "FAIL" : "PASS", BYTES, stage);
    return result;
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    if (argc == 2 && !strcmp(argv[1], "--child")) return child();
    if (argc != 2 || strcmp(argv[1], "run") || argv[0][0] != '/') {
        fputs("usage: /absolute/path/whyred-surface-ipc run\n", stderr); return 2;
    }
    @autoreleasepool { return parent(argv[0]); }
}
