/* SPDX-License-Identifier: MIT
 * Opt-in process-local HakiOS EAGL bridge. The ordinary boot keeps Apple's
 * existing software renderer. No fixed-address iOS code patches are needed.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sysctl.h>
#include <unistd.h>

__attribute__((constructor)) static void install(void)
{
    char args[1024] = {0}; size_t size = sizeof(args) - 1;
    if (sysctlbyname("kern.bootargs", args, &size, NULL, 0)) return;
    int enabled = 0;
    for (char *s = strtok(args, " "); s; s = strtok(NULL, " "))
        if (!strcmp(s, "sweetgles=1")) enabled = 1;
    if (!enabled) return;
    fprintf(stderr, "SWEET GLES: enabling EAGL bridge in %s\n", getprogname());
    if (!dlopen("/System/Library/Frameworks/OpenGLES.framework/OpenGLES", RTLD_NOW | RTLD_GLOBAL) ||
        !dlopen("/usr/local/sweet/lib/libsweet-gles.dylib", RTLD_NOW | RTLD_LOCAL)) {
        fprintf(stderr, "SWEET GLES: bridge load failed: %s\n", dlerror());
        return;
    }
    fprintf(stderr, "SWEET GLES: EAGL bridge loaded; backend=softpipe hardware_claim=0\n");
}
