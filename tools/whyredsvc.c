/*
 * BSD 2-Clause License
 * 
 * Copyright (c) 2022-2023 Procursus Team <team@procurs.us>
 * All rights reserved.
 * 
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 * 
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions and the following disclaimer.
 * 
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 * 
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 * 
 */
/* Restricted job control for the developer-owned whyred bring-up.
 * RPC schema: ProcursusTeam/launchctl, commit
 * 22906f7ddaf11ff550da9a2bc5771e3f108fc193 (enable.c/bootstrap.c/xpc_helper.c).
 * Only two named jobs, explicit system or user501 domain; no whole-domain RPC.
 */
#include <dlfcn.h>
#include <errno.h>
#include <inttypes.h>
#include <mach/mach.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sysctl.h>
#include <unistd.h>
#include <xpc/xpc.h>

struct alloc_once { long once; void *ptr; };
struct xpc_globals { uint64_t a, flags; mach_port_t port; uint32_t pad; void *pipe; };
typedef int (*interface_routine_t)(void *, uint64_t, xpc_object_t, xpc_object_t *, uint64_t);

static int parse(const char *action, const char *domain, const char *label, uint64_t *routine,
    uint64_t *type, uint64_t *handle) {
    if (strcmp(label, "com.apple.bluetoothd") && strcmp(label, "com.apple.fairplayd.H2")) return 2;
    if (!strcmp(domain, "system")) { *type = 1; *handle = 0; }
    else if (!strcmp(domain, "user501")) { *type = 2; *handle = 501; }
    else return 2;
    if (!strcmp(action, "status")) *routine = 712;
    else if (!strcmp(action, "disable")) *routine = 809;
    else if (!strcmp(action, "enable")) *routine = 808;
    else if (!strcmp(action, "bootout")) *routine = 801;
    else if (!strcmp(action, "bootstrap")) *routine = 800;
    else return 2;
    return 0;
}

static bool whyred_boot(void) {
    char args[4096]; size_t size = sizeof(args);
    if (sysctlbyname("kern.bootargs", args, &size, NULL, 0) || size >= sizeof(args)) return false;
    args[size] = 0;
    const char *p = strstr(args, "-whyred-platform");
    return p && (p == args || p[-1] == ' ') && (p[16] == 0 || p[16] == ' ');
}

int main(int argc, char **argv) {
    if (argc != 4 && !(argc == 5 && !strcmp(argv[4], "--dry-run"))) {
        fprintf(stderr, "usage: whyredsvc {status|disable|bootout|enable|bootstrap} {system|user501} {com.apple.bluetoothd|com.apple.fairplayd.H2} [--dry-run]\n");
        return 2;
    }
    uint64_t routine, type, handle;
    if (parse(argv[1], argv[2], argv[3], &routine, &type, &handle)) {
        fprintf(stderr, "Refusing action, domain or label outside the two-job allowlist\n"); return 2;
    }
    bool dry = argc == 5;
    if (!dry && (getuid() || geteuid() || !whyred_boot())) {
        fprintf(stderr, "Refusing RPC outside a root whyred boot\n"); return 3;
    }
    xpc_object_t message = xpc_dictionary_create(NULL, NULL, 0), reply = NULL;
    if (!message) return 1;
    xpc_dictionary_set_uint64(message, "subsystem", routine >> 8);
    xpc_dictionary_set_uint64(message, "routine", routine);
    xpc_dictionary_set_uint64(message, "type", type);
    xpc_dictionary_set_uint64(message, "handle", handle);
    if (routine == 800) {
        char path[160];
        int n = snprintf(path, sizeof(path), "/System/Library/LaunchDaemons/%s.plist", argv[3]);
        if (n < 0 || (size_t)n >= sizeof(path)) return 2;
        xpc_object_t paths = xpc_array_create(NULL, 0);
        xpc_array_set_string(paths, XPC_ARRAY_APPEND, path);
        xpc_dictionary_set_value(message, "paths", paths); xpc_release(paths);
    } else {
        xpc_dictionary_set_string(message, "name", argv[3]);
    }
    if (routine == 808 || routine == 809) {
        xpc_object_t names = xpc_array_create(NULL, 0);
        xpc_array_set_string(names, XPC_ARRAY_APPEND, argv[3]);
        xpc_dictionary_set_value(message, "names", names); xpc_release(names);
    }
    if (routine == 801) xpc_dictionary_set_bool(message, "no-einprogress", true);
    printf("action=%s domain=%s label=%s routine=%" PRIu64 " dry_run=%d\n", argv[1], argv[2], argv[3], routine, dry);
    fflush(stdout);
    if (dry) { xpc_release(message); return 0; }
    struct alloc_once *table = dlsym(RTLD_DEFAULT, "_os_alloc_once_table");
    interface_routine_t call = (interface_routine_t)dlsym(RTLD_DEFAULT, "_xpc_pipe_interface_routine");
    struct xpc_globals *globals = table ? table[1].ptr : NULL;
    mach_port_type_t port_type = 0;
    if (!call || !globals || !globals->pipe || !MACH_PORT_VALID(globals->port) ||
        mach_port_type(mach_task_self(), globals->port, &port_type) || !(port_type & MACH_PORT_TYPE_SEND)) {
        fprintf(stderr, "XPC bootstrap interface unavailable\n"); xpc_release(message); return 1;
    }
    alarm(30);
    int transport = call(globals->pipe, 0, message, &reply, 0);
    alarm(0); xpc_release(message);
    if (transport || !reply || xpc_get_type(reply) != XPC_TYPE_DICTIONARY) {
        fprintf(stderr, "Launchd transport/response failure: %d\n", transport);
        if (reply) xpc_release(reply); return 1;
    }
    int64_t error = xpc_dictionary_get_int64(reply, "error");
    if (!error && routine == 800) error = xpc_dictionary_get_int64(reply, "bootstrap-error");
    if (!error && routine == 801) error = xpc_dictionary_get_int64(reply, "bootout-error");
    xpc_object_t errors = xpc_dictionary_get_value(reply, "errors");
    if (!error && errors && (xpc_get_type(errors) != XPC_TYPE_DICTIONARY || xpc_dictionary_get_count(errors))) error = EIO;
    const char *(*explain)(int) = (const char *(*)(int))dlsym(RTLD_DEFAULT, "xpc_strerror");
    if (error && explain) fprintf(stderr, "Launchd: %s\n", explain((int)error));
    char *description = xpc_copy_description(reply);
    printf("launchd_error=%" PRId64 " reply=%.8192s\n", error, description ? description : "(unavailable)");
    free(description); xpc_release(reply);
    return error ? 1 : 0;
}
