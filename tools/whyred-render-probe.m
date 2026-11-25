/* Bounded developer graphics probes. Bitmap/capture modes do not present frames.
 * Explicit remote-layer creates and invalidates one small visible test layer.
 * Explicit present modes queue a real server capture on the verified whyred97/98/99 framebuffer.
 * Explicit live modes capture each new frame into fresh immutable surface storage.
 * No files, renderer configuration or daemon changes. */
#import <Foundation/Foundation.h>
#import <CoreImage/CoreImage.h>
#import <QuartzCore/QuartzCore.h>
#import <ImageIO/ImageIO.h>
#include <mach/mach.h>
#if __has_include(<IOSurface/IOSurface.h>) && !defined(WHYRED_PROBE_IOSURFACE_DECLS)
#import <IOSurface/IOSurface.h>
#else
/* The iPhoneOS SDK ships the dylib without its C headers. Keep this small
 * declaration set aligned with the ABI of the tested IOSurface entry points. */
typedef struct __IOSurface *IOSurfaceRef;
extern const CFStringRef kIOSurfaceWidth, kIOSurfaceHeight;
extern const CFStringRef kIOSurfaceBytesPerElement, kIOSurfaceBytesPerRow;
extern const CFStringRef kIOSurfaceAllocSize, kIOSurfacePixelFormat;
extern IOSurfaceRef IOSurfaceCreate(CFDictionaryRef);
extern kern_return_t IOSurfaceLock(IOSurfaceRef, uint32_t, uint32_t *);
extern kern_return_t IOSurfaceUnlock(IOSurfaceRef, uint32_t, uint32_t *);
extern size_t IOSurfaceGetWidth(IOSurfaceRef), IOSurfaceGetHeight(IOSurfaceRef);
extern size_t IOSurfaceGetBytesPerRow(IOSurfaceRef);
extern void *IOSurfaceGetBaseAddress(IOSurfaceRef);
extern uint32_t IOSurfaceGetID(IOSurfaceRef);

#endif
#import <TargetConditionals.h>
#if TARGET_OS_IPHONE && !TARGET_OS_SIMULATOR
#import <OpenGLES/EAGL.h>
#import <OpenGLES/ES2/gl.h>
#endif
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <dlfcn.h>
#include <objc/runtime.h>
#include <unistd.h>
#include <signal.h>
#include <sys/resource.h>
#include <time.h>
#include <sys/sysctl.h>

@interface NSObject (WhyredContextProbe)
+ (id)remoteContextWithOptions:(NSDictionary *)options;
- (void)setLayer:(CALayer *)layer;
- (void)setLevel:(float)level;
- (uint32_t)contextId;
- (void)invalidate;
@end

static int bitmap(void) {
    puts("WHYRED RENDER: software context begin");
    CIContext *context = [CIContext contextWithOptions:@{
        kCIContextUseSoftwareRenderer: @YES,
        kCIContextCacheIntermediates: @NO
    }];
    printf("WHYRED RENDER: software context=%s\n", context ? "created" : "nil");
    if (!context) return 1;
    CIColor *red = [CIColor colorWithRed:1 green:0 blue:0 alpha:1];
    CGRect bounds = CGRectMake(0, 0, 16, 16);
    CIImage *image = [[CIImage imageWithColor:red] imageByCroppingToRect:bounds];
    unsigned char pixels[16 * 16 * 4];
    memset(pixels, 0x6d, sizeof(pixels));
    CGColorSpaceRef color = CGColorSpaceCreateDeviceRGB();
    if (!color) return 1;
    puts("WHYRED RENDER: software render begin");
    [context render:image toBitmap:pixels rowBytes:16 * 4 bounds:bounds
             format:kCIFormatRGBA8 colorSpace:color];
    CGColorSpaceRelease(color);
    unsigned matches = 0;
    for (unsigned i = 0; i < 16 * 16; i++) {
        const unsigned char *p = pixels + 4 * i;
        if (p[0] == 255 && p[1] == 0 && p[2] == 0 && p[3] == 255) matches++;
    }
    printf("WHYRED RENDER: software pixels=%u/256 first=%u,%u,%u,%u files_written=0\n",
           matches, pixels[0], pixels[1], pixels[2], pixels[3]);
    return matches == 256 ? 0 : 1;
}

static int eagl(void) {
#if TARGET_OS_IPHONE && !TARGET_OS_SIMULATOR
    unsigned successes = 0;
    for (unsigned api = 2; api <= 3; api++) {
        printf("WHYRED RENDER: EAGL api=%u begin\n", api);
        EAGLContext *context = [[EAGLContext alloc] initWithAPI:(EAGLRenderingAPI)api];
        BOOL current = context && [EAGLContext setCurrentContext:context];
        printf("WHYRED RENDER: EAGL api=%u context=%s current=%d\n",
               api, context ? "created" : "nil", current);
        if (current) {
            const GLubyte *renderer = glGetString(GL_RENDERER);
            GLenum error = glGetError();
            printf("WHYRED RENDER: EAGL api=%u renderer=%.*s error=0x%x\n",
                   api, 256, renderer ? (const char *)renderer : "(null)", error);
            if (renderer && error == GL_NO_ERROR) successes++;
        }
        [EAGLContext setCurrentContext:nil];
    }
    return successes ? 0 : 1;
#else
    puts("WHYRED RENDER: EAGL unavailable for this build target");
    return 2;
#endif
}

static int layer_draw(unsigned char *pixels) {
    /* Test QuartzCore's layer-to-CoreGraphics path separately from CoreImage. */
    CGColorSpaceRef color = CGColorSpaceCreateWithName(kCGColorSpaceSRGB);
    CGContextRef bitmap = CGBitmapContextCreate(pixels, 16, 16, 8, 16 * 4, color,
        kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Big);
    CGColorSpaceRelease(color);
    if (!bitmap) return 1;
    puts("WHYRED RENDER: layer bitmap created");
    CALayer *root = [CALayer layer];
    root.frame = CGRectMake(0, 0, 16, 16);
    CGColorRef red = CGColorCreateSRGB(1, 0, 0, 1);
    CGColorRef green = CGColorCreateSRGB(0, 1, 0, 1);
    root.backgroundColor = red;
    CALayer *child = [CALayer layer];
    child.frame = CGRectMake(4, 4, 8, 8);
    child.backgroundColor = green;
    [root addSublayer:child];
    CGColorRelease(red); CGColorRelease(green);
    puts("WHYRED RENDER: layer render begin");
    [root renderInContext:bitmap];
    CGContextRelease(bitmap);
    printf("WHYRED RENDER: layer first=%u,%u,%u,%u center=%u,%u,%u,%u\n", pixels[0], pixels[1], pixels[2], pixels[3], pixels[544], pixels[545], pixels[546], pixels[547]);
    unsigned red_count = 0, green_count = 0;
    for (unsigned i = 0; i < 256; i++) {
        const unsigned char *p = pixels + i * 4;
        if (p[0] == 255 && p[1] == 0 && p[2] == 0 && p[3] == 255) red_count++;
        if (p[0] == 0 && p[1] == 255 && p[2] == 0 && p[3] == 255) green_count++;
    }
    printf("WHYRED RENDER: layer red=%u/192 green=%u/64 files_written=0\n",
           red_count, green_count);
    return red_count == 192 && green_count == 64 ? 0 : 1;
}

static int layer_bitmap(void) {
    unsigned char pixels[16 * 16 * 4] = {0};
    return layer_draw(pixels);
}

static int surface_bitmap(void) {
    NSDictionary *properties = @{
        (NSString *)kIOSurfaceWidth: @16, (NSString *)kIOSurfaceHeight: @16,
        (NSString *)kIOSurfaceBytesPerElement: @4,
        (NSString *)kIOSurfaceBytesPerRow: @64,
        (NSString *)kIOSurfaceAllocSize: @1024,
        (NSString *)kIOSurfacePixelFormat: @(0x52474241u)
    };
    IOSurfaceRef surface = IOSurfaceCreate((__bridge CFDictionaryRef)properties);
    printf("WHYRED RENDER: surface created=%d\n", surface != NULL);
    if (!surface) return 1;
    uint32_t seed = 0;
    kern_return_t kr = IOSurfaceLock(surface, 0, &seed);
    printf("WHYRED RENDER: surface lock=0x%x width=%zu height=%zu stride=%zu\n",
           kr, IOSurfaceGetWidth(surface), IOSurfaceGetHeight(surface),
           IOSurfaceGetBytesPerRow(surface));
    if (kr || IOSurfaceGetWidth(surface) != 16 || IOSurfaceGetHeight(surface) != 16 ||
        IOSurfaceGetBytesPerRow(surface) != 64 || !IOSurfaceGetBaseAddress(surface)) {
        if (!kr) IOSurfaceUnlock(surface, 0, NULL);
        CFRelease(surface); return 1;
    }
    unsigned char expected[1024];
    unsigned char *base = IOSurfaceGetBaseAddress(surface);
    memset(base, 0, sizeof(expected));
    int result = layer_draw(base);
    memcpy(expected, base, sizeof(expected));
    kr = IOSurfaceUnlock(surface, 0, &seed);
    if (kr) result = 1;
    kern_return_t lock_kr = IOSurfaceLock(surface, 1 /* read-only lock */, &seed);
    int preserved = !lock_kr && IOSurfaceGetBaseAddress(surface) &&
        !memcmp(expected, IOSurfaceGetBaseAddress(surface), sizeof(expected));
    printf("WHYRED RENDER: surface unlock=0x%x relock=0x%x preserved=%d display_changed=0\n",
           kr, lock_kr, preserved);
    if (!lock_kr) IOSurfaceUnlock(surface, 1 /* read-only lock */, NULL);
    CFRelease(surface);
    return result || !preserved ? 1 : 0;
}

static int renderer_methods(void) {
    const char *classes[] = {"CAWindowServer", "CAWindowServerDisplay", "CARenderer", "CAContext"};
    for (unsigned c = 0; c < sizeof(classes) / sizeof(classes[0]); c++) {
        Class cls = objc_getClass(classes[c]);
        printf("WHYRED RENDER: class=%s present=%d\n", classes[c], cls != Nil);
        if (!cls) continue;
        for (unsigned meta = 0; meta < 2; meta++) {
            unsigned count = 0, printed = 0;
            Method *methods = class_copyMethodList(meta ? object_getClass(cls) : cls, &count);
            for (unsigned i = 0; i < count && printed < 128; i++) {
                const char *name = sel_getName(method_getName(methods[i]));
                if (!strcasestr(name, "render") && !strcasestr(name, "display") &&
                    !strcasestr(name, "init") && !strcasestr(name, "server") &&
                    !strcasestr(name, "context") && !strcasestr(name, "layer") &&
                    !strcasestr(name, "level") && !strcasestr(name, "invalidate")) continue;
                IMP imp = method_getImplementation(methods[i]);
                Dl_info info = {0};
                if (!dladdr((const void *)imp, &info) || !info.dli_fbase) continue;
                printf("WHYRED RENDER: method=%c[%s %s] offset=0x%llx types=%s\n",
                       meta ? '+' : '-', classes[c], name,
                       (unsigned long long)((uintptr_t)imp - (uintptr_t)info.dli_fbase),
                       method_getTypeEncoding(methods[i]));
                printed++;
            }
            free(methods);
        }
    }
    return 0;
}

static size_t last_capture_marker_pixels, last_capture_rgb, last_capture_alpha;
static uint32_t last_capture_hash;
static BOOL live_quiet, live_allow_black;
#if TARGET_OS_IPHONE && !TARGET_OS_SIMULATOR
static volatile sig_atomic_t live_stop;
static void stop_live(int signal_number) { (void)signal_number; live_stop = 1; }
static double monotonic_seconds(void) {
    struct timespec t = {0};
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return -1;
    return (double)t.tv_sec + (double)t.tv_nsec / 1000000000.0;
}

#endif
static int present_surface(IOSurfaceRef surface) {
    /* Public IOKit C ABI; selector/record layout belongs to our own driver.
     * Fail closed before accessing an incompatible installed kernel. */
    char uuid[80] = {0}; size_t uuid_size = sizeof(uuid);
    if (sysctlbyname("kern.uuid", uuid, &uuid_size, NULL, 0) ||
        (strcmp(uuid, "1444AADE-E57B-3F55-88A9-866FFA6086A0") &&
         strcmp(uuid, "936C980F-9428-33A1-B076-CDB09ABDC855") &&
         strcmp(uuid, "2ED4E8A4-6D1C-3C3C-980B-8533C25978D1"))) {
        puts("WHYRED RENDER: present refused incompatible kernel"); return 1;
    }
    typedef uint32_t IOName;
    CFMutableDictionaryRef (*matching)(const char *) = dlsym(RTLD_DEFAULT, "IOServiceMatching");
    IOName (*get_service)(mach_port_t, CFDictionaryRef) = dlsym(RTLD_DEFAULT, "IOServiceGetMatchingService");
    kern_return_t (*open_service)(IOName, mach_port_t, uint32_t, IOName *) = dlsym(RTLD_DEFAULT, "IOServiceOpen");
    kern_return_t (*release_object)(IOName) = dlsym(RTLD_DEFAULT, "IOObjectRelease");
    kern_return_t (*close_service)(IOName) = dlsym(RTLD_DEFAULT, "IOServiceClose");
    kern_return_t (*scalar)(IOName, uint32_t, const uint64_t *, uint32_t, uint64_t *, uint32_t *) =
        dlsym(RTLD_DEFAULT, "IOConnectCallScalarMethod");
    kern_return_t (*structure)(IOName, uint32_t, const void *, size_t, void *, size_t *) =
        dlsym(RTLD_DEFAULT, "IOConnectCallStructMethod");
    if (!matching || !get_service || !open_service || !release_object || !close_service || !scalar || !structure) return 1;
    CFMutableDictionaryRef match = matching("AppleCLCD");
    if (!match) return 1;
    IOName service = get_service(MACH_PORT_NULL, match), connection = 0;
    if (!service) return 1;
    kern_return_t kr = open_service(service, mach_task_self(), 0, &connection);
    release_object(service);
    if (kr) return 1;
    int result = 1;
    uint64_t values[2] = {0}; uint32_t count = 1;
    kr = scalar(connection, 7, NULL, 0, values, &count);
    if (kr || count != 1 || values[0] != 0) goto done;
    count = 2;
    kr = scalar(connection, 8, NULL, 0, values, &count);
    if (kr || count != 2 || values[0] != 1125 || values[1] != 2436) goto done;
    count = 1;
    kr = scalar(connection, 4, NULL, 0, values, &count);
    if (kr || count != 1 || values[0] > UINT32_MAX) goto done;
    {
        uint32_t id = IOSurfaceGetID(surface), swap = (uint32_t)values[0];
        if (!id) goto done;
        uint8_t record[0x46c] = {0};
        uint32_t set = 1, clear = 0xe, rect[4] = {0, 0, 1125, 2436};
        memcpy(record + 0x50, &swap, 4); memcpy(record + 0x54, &id, 4);
        memcpy(record + 0x64, rect, sizeof(rect)); memcpy(record + 0xc4, rect, sizeof(rect));
        memcpy(record + 0x104, &set, 4); memcpy(record + 0x108, &clear, 4);
        size_t output_size = 0;
        kr = structure(connection, 5, record, sizeof(record), NULL, &output_size);
        if (!live_quiet) printf("WHYRED RENDER: real capture queued swap=%u surface=%u kr=0x%x presentation_requested=%d\n",
               swap, id, kr, kr == KERN_SUCCESS);
        result = kr != KERN_SUCCESS;
    }
done:
    close_service(connection);
    return result;
}

static int capture_display(BOOL export_png, unsigned present_count) {
#if !TARGET_OS_IPHONE || TARGET_OS_SIMULATOR
    puts("WHYRED RENDER: display capture requires the physical iOS target");
    return 1;
#endif
    /* Same five-argument call used by this system's backboardd screenshot path.
     * The destination is our own surface; this does not present a frame. */
    typedef int (*RenderDisplay)(mach_port_t, CFStringRef, IOSurfaceRef, int, int);
    RenderDisplay render = (RenderDisplay)dlsym(RTLD_DEFAULT, "CARenderServerRenderDisplay");
    if (!render) { puts("WHYRED RENDER: display capture API absent"); return 1; }
    const size_t width = 1125, height = 2436, stride = 4544;
    NSDictionary *properties = @{
        (NSString *)kIOSurfaceWidth: @(width), (NSString *)kIOSurfaceHeight: @(height),
        (NSString *)kIOSurfaceBytesPerElement: @4,
        (NSString *)kIOSurfaceBytesPerRow: @(stride),
        (NSString *)kIOSurfaceAllocSize: @(stride * height),
        (NSString *)kIOSurfacePixelFormat: @(0x42475241u)
    };
    IOSurfaceRef surface = IOSurfaceCreate((__bridge CFDictionaryRef)properties);
    if (!surface) return 1;
    kern_return_t kr = IOSurfaceLock(surface, 0, NULL);
    if (kr || !IOSurfaceGetBaseAddress(surface) || IOSurfaceGetBytesPerRow(surface) != stride ||
        IOSurfaceGetWidth(surface) != width || IOSurfaceGetHeight(surface) != height) {
        if (!kr) IOSurfaceUnlock(surface, 0, NULL);
        CFRelease(surface); return 1;
    }
    memset(IOSurfaceGetBaseAddress(surface), 0, stride * height);
    if (!live_quiet) puts("WHYRED RENDER: display capture LCD begin display_changed=0");
    int accepted = render(MACH_PORT_NULL, CFSTR("LCD"), surface, 0, 0);
    size_t rgb = 0, alpha = 0, marker = 0;
    uint32_t hash = 2166136261U;
    const unsigned char *base = IOSurfaceGetBaseAddress(surface);
    for (size_t y = 0; y < height; y++) for (size_t x = 0; x < width; x++) {
        const unsigned char *p = base + y * stride + x * 4;
        if (live_quiet) hash = (hash ^ ((uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24)) * 16777619U;
        rgb += (p[0] | p[1] | p[2]) != 0;
        alpha += p[3] != 0;
        marker += p[2] >= 210 && p[1] >= 30 && p[1] <= 90 && p[0] <= 80 && p[3] >= 240;
    }
    if (!live_quiet) printf("WHYRED RENDER: display capture accepted=%d rgb=%zu alpha=%zu pixels=%zu marker=%zu\n",
           accepted, rgb, alpha, width * height, marker);
    last_capture_marker_pixels = accepted ? marker : 0;
    last_capture_rgb = accepted ? rgb : 0;
    last_capture_alpha = accepted ? alpha : 0;
    last_capture_hash = accepted ? hash : 0;
    /* Opaque black is a valid fresh scene. An untouched transparent destination
     * is not evidence that the server drew anything. Existing probes stay strict. */
    BOOL drawn = accepted && (rgb || (live_allow_black && alpha));
    BOOL exported = !export_png;
    if (export_png && accepted && rgb) {
        /* Encode our locked capture surface, never the panel mapping. The
         * caller receives base64 on stdout; no file is written on the phone. */
        CGColorSpaceRef space = CGColorSpaceCreateWithName(kCGColorSpaceSRGB);
        CGDataProviderRef provider = CGDataProviderCreateWithData(NULL, base, stride * height, NULL);
        CGImageRef image = space && provider ? CGImageCreate(width, height, 8, 32, stride,
            space, kCGBitmapByteOrder32Little | kCGImageAlphaPremultipliedFirst,
            provider, NULL, false, kCGRenderingIntentDefault) : NULL;
        NSMutableData *png = [NSMutableData data];
        CGImageDestinationRef destination = image ? CGImageDestinationCreateWithData(
            (__bridge CFMutableDataRef)png, CFSTR("public.png"), 1, NULL) : NULL;
        if (destination) {
            CGImageDestinationAddImage(destination, image, NULL);
            exported = CGImageDestinationFinalize(destination);
            if (exported) printf("WHYRED RENDER PNG: %s\n", [[png base64EncodedStringWithOptions:0] UTF8String]);
            CFRelease(destination);
        }
        if (image) CGImageRelease(image);
        if (provider) CGDataProviderRelease(provider);
        if (space) CGColorSpaceRelease(space);
    }
    BOOL presented = !present_count;
    if (present_count && drawn) {
        /* A finite observation window: repeat the same real captured frame.
         * No renderer/daemon changes, no synthetic content or persistent loop. */
        unsigned completed = 0;
        if (present_count > 101) { IOSurfaceUnlock(surface, 0, NULL); CFRelease(surface); return 1; }
        if (!live_quiet) printf("WHYRED RENDER: observation begin submissions=%u interval_ms=100 fixed_capture=1 visible_output_unverified=1\n", present_count);
        for (unsigned n = 0; n < present_count; n++) {
            if (n) usleep(100000);
            if (present_surface(surface)) break;
            completed++;
        }
        presented = completed == present_count;
        if (!live_quiet) printf("WHYRED RENDER: observation end completed=%u requested=%u visible_output_unverified=1\n", completed, present_count);
    }
    kr = IOSurfaceUnlock(surface, 0, NULL);
    CFRelease(surface);
    return drawn && exported && presented && !kr ? 0 : 1;
}

/* Real server CPU capture -> own framebuffer, at most one new frame/second.
 * Every capture owns NEW surface storage; the kernel retains queued surfaces
 * until replacement/presentation. Never rewrite memory that scanout may read.
 * No stored screenshot, test layer, power override, renderer flag or fake GPU.
 * live-window is the finite pilot; live runs only when explicitly invoked. */
static int live_display(BOOL continuous) {
#if !TARGET_OS_IPHONE || TARGET_OS_SIMULATOR
    (void)continuous;
    puts("WHYRED RENDER: live display requires the physical iOS target"); return 1;
#else
    char uuid[80] = {0}; size_t length = sizeof(uuid);
    if (sysctlbyname("kern.uuid", uuid, &length, NULL, 0) ||
        (strcmp(uuid, "1444AADE-E57B-3F55-88A9-866FFA6086A0") &&
         strcmp(uuid, "936C980F-9428-33A1-B076-CDB09ABDC855") &&
         strcmp(uuid, "2ED4E8A4-6D1C-3C3C-980B-8533C25978D1"))) {
        puts("WHYRED DISPLAY: incompatible kernel; no frame submitted"); return 1;
    }
    double start = monotonic_seconds();
    if (start < 0) return 1;
    struct sigaction action = {0}; action.sa_handler = stop_live;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGTERM, &action, NULL) || sigaction(SIGINT, &action, NULL)) return 1;
    /* Terminate a stuck individual capture. Default SIGALRM cleanup is handled
     * by process teardown, including its IOKit/IOSurface rights. */
    signal(SIGALRM, SIG_DFL);
    /* This process can be supervised with stdout/stderr in RAMFS. Bound its
     * regular log files; reaching the cap must not terminate frame updates. */
    struct rlimit log_limit;
    if (getrlimit(RLIMIT_FSIZE, &log_limit)) return 1;
    if (log_limit.rlim_cur > 1024 * 1024) log_limit.rlim_cur = 1024 * 1024;
    if (log_limit.rlim_max > 1024 * 1024) log_limit.rlim_max = 1024 * 1024;
    if (signal(SIGXFSZ, SIG_IGN) == SIG_ERR || setrlimit(RLIMIT_FSIZE, &log_limit)) return 1;
    live_quiet = YES; live_allow_black = YES; live_stop = 0;
    unsigned frames = 0, errors = 0, consecutive_errors = 0;
    uint32_t previous_hash = 0; unsigned changes = 0;
    puts("WHYRED DISPLAY: live begin new_capture_per_frame=1 max_fps=1 power_override=0");
    while (!live_stop && (continuous || monotonic_seconds() - start < 40)) {
        double before = monotonic_seconds();
        if (before < 0) { errors++; consecutive_errors = 3; break; }
        alarm(45);
        int result;
        @autoreleasepool { result = capture_display(NO, 1); }
        alarm(0);
        double after = monotonic_seconds();
        if (after < 0) { errors++; consecutive_errors = 3; break; }
        if (!result) {
            if (frames && last_capture_hash != previous_hash) changes++;
            previous_hash = last_capture_hash;
            frames++; consecutive_errors = 0;
        } else { errors++; consecutive_errors++; }
        if (frames <= 3 || frames % 10 == 0 || result)
            printf("WHYRED DISPLAY: frames=%u errors=%u rgb=%zu alpha=%zu hash=%08x changes=%u capture_ms=%.1f\n",
                frames, errors, last_capture_rgb, last_capture_alpha, last_capture_hash,
                changes, (after - before) * 1000.0);
        if (consecutive_errors >= 3) break;
        while (!live_stop) {
            double now = monotonic_seconds();
            if (now < 0) { errors++; consecutive_errors = 3; live_stop = 1; break; }
            if (now - before >= 1.0) break;
            usleep(100000);
        }
    }
    live_quiet = NO; live_allow_black = NO;
    printf("WHYRED DISPLAY: live end frames=%u errors=%u changes=%u stopped=%d elapsed_s=%.2f\n",
           frames, errors, changes, live_stop != 0, monotonic_seconds() - start);
    return (continuous ? frames != 0 && consecutive_errors < 3 : frames >= 3 && !errors) ? 0 : 1;
#endif
}

static int remote_layer(BOOL named_display, unsigned hold_seconds) {
#if !TARGET_OS_IPHONE || TARGET_OS_SIMULATOR
    (void)hold_seconds;
    puts("WHYRED RENDER: remote layer requires the physical iOS target");
    return 1;
#endif
    Class cls = objc_getClass("CAContext");
    if (!cls) return 1;
    const char *names[] = {"remoteContextWithOptions:", "setLayer:", "invalidate", "contextId"};
    const char *types[] = {"@24@0:8@16", "v24@0:8@16", "v16@0:8", "I16@0:8"};
    for (unsigned i = 0; i < 4; i++) {
        SEL sel = sel_registerName(names[i]);
        Method method = i ? class_getInstanceMethod(cls, sel) : class_getClassMethod(cls, sel);
        if (!method || strcmp(method_getTypeEncoding(method), types[i])) {
            printf("WHYRED RENDER: context ABI unavailable method=%s\n", names[i]);
            return 1;
        }
    }
    /* Match the capture's LCD name explicitly in the named variant. Keep the
     * original ID=0 command available for an otherwise identical comparison. */
    CFStringRef *display = dlsym(RTLD_DEFAULT,
                               named_display ? "kCAContextDisplayName" : "kCAContextDisplayId");
    CFStringRef *displayable = dlsym(RTLD_DEFAULT, "kCAContextDisplayable");
    CFStringRef *ignore = dlsym(RTLD_DEFAULT, "kCAContextIgnoresHitTest");
    if (!display || !*display || !displayable || !*displayable || !ignore || !*ignore) return 1;
    NSDictionary *options = @{
        (__bridge NSString *)*display: named_display ? (id)@"LCD" : (id)@0,
        (__bridge NSString *)*displayable: @YES,
        (__bridge NSString *)*ignore: @YES
    };
    printf("WHYRED RENDER: remote context baseline route=%s\n", named_display ? "name:LCD" : "id:0");
    (void)capture_display(NO, NO);
    size_t baseline_marker = last_capture_marker_pixels;
    id context = [cls remoteContextWithOptions:options];
    printf("WHYRED RENDER: remote context created=%d\n", context != nil);
    if (!context) return 1;
    int result = 1;
    @try {
        uint32_t context_id = [context contextId];
        printf("WHYRED RENDER: remote context id=%u route=%s\n", context_id,
               named_display ? "name:LCD" : "id:0");
        if (!context_id) return 1;
        CALayer *root = [CALayer layer];
        root.frame = CGRectMake(0, 0, 1125, 2436);
        CALayer *marker = [CALayer layer];
        marker.frame = CGRectMake(16, 16, 32, 32);
        CGColorRef color = CGColorCreateSRGB(229.0 / 255, 57.0 / 255, 53.0 / 255, 1);
        marker.backgroundColor = color;
        CGColorRelease(color);
        [root addSublayer:marker];
        [context setLayer:root];
        Method level = class_getInstanceMethod(cls, sel_registerName("setLevel:"));
        if (level && !strcmp(method_getTypeEncoding(level), "v20@0:8f16")) [context setLevel:9000];
        [CATransaction flush];
        puts("WHYRED RENDER: remote marker submitted temporary=1 ignores_hit_test=1");
        usleep(1000000);
        result = capture_display(NO, NO);
        printf("WHYRED RENDER: remote marker baseline=%zu after=%zu\n",
               baseline_marker, last_capture_marker_pixels);
        if (last_capture_marker_pixels < baseline_marker + 900) result = 1;
        if (!result && hold_seconds) {
            printf("WHYRED RENDER: marker visible observation seconds=%u temporary=1\n", hold_seconds);
            sleep(hold_seconds);
        }
    } @finally {
        [context setLayer:nil];
        [context invalidate];
        [CATransaction flush];
        puts("WHYRED RENDER: remote marker context invalidated");
    }
    return result;
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    @autoreleasepool {
        @try {
            if (argc == 2 && !strcmp(argv[1], "software")) return bitmap();
            if (argc == 2 && !strcmp(argv[1], "eagl")) return eagl();
            if (argc == 2 && !strcmp(argv[1], "layer")) return layer_bitmap();
            if (argc == 2 && !strcmp(argv[1], "surface")) return surface_bitmap();
            if (argc == 2 && !strcmp(argv[1], "methods")) return renderer_methods();
            if (argc == 2 && !strcmp(argv[1], "capture")) return capture_display(NO, NO);
            if (argc == 2 && !strcmp(argv[1], "capture-png")) return capture_display(YES, NO);
            if (argc == 2 && !strcmp(argv[1], "present-once")) return capture_display(NO, 1);
            if (argc == 2 && !strcmp(argv[1], "present-window")) return capture_display(NO, 101);
            if (argc == 2 && !strcmp(argv[1], "live-window")) return live_display(NO);
            if (argc == 2 && !strcmp(argv[1], "live")) return live_display(YES);
            if (argc == 2 && !strcmp(argv[1], "remote-layer")) return remote_layer(NO, 0);
            if (argc == 2 && !strcmp(argv[1], "remote-layer-lcd")) return remote_layer(YES, 0);
            if (argc == 2 && !strcmp(argv[1], "remote-layer-lcd-window")) return remote_layer(YES, 10);
            fputs("usage: whyred-render-probe software | eagl | layer | surface | methods | capture | capture-png | present-once | present-window | live-window | live | remote-layer | remote-layer-lcd | remote-layer-lcd-window\n", stderr);
            return 2;
        } @catch (NSException *exception) {
            printf("WHYRED RENDER: exception=%.*s reason=%.*s\n", 256,
                   exception.name.UTF8String, 512, exception.reason.UTF8String);
            return 1;
        }
    }
}
