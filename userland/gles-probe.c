/* SPDX-License-Identifier: MIT
 * Real GLES shaders -> readback -> IOSurface -> existing AppleCLCD swaps.
 * OSMesa's ES profile is the small HakiOS extension, not desktop GL.
 * The renderer string, pixel checks and presentation are separate evidence.
 */
#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/IOKitLib.h>
#include <IOSurface/IOSurfaceRef.h>
#include <mach/mach_time.h>
#include <GL/osmesa.h>
#include <GLES2/gl2.h>
#include <dlfcn.h>
#include <objc/message.h>
#include <objc/runtime.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifndef SWEET_GLES_HARDWARE
#define SWEET_GLES_HARDWARE 0
#endif

enum { W = 256, H = 256 };
static unsigned char pixels[W * H * 4], window[16 * 16 * 4];
static io_connect_t fb;
static IOSurfaceRef surface;
static unsigned width, height;

static void fail(const char *what, unsigned code)
{
    printf("SWEET GLES: FAIL %s code=0x%x gl=0x%x\n", what, code, glGetError());
    fflush(stdout);
    /* PID 1 must not exit; allow the persistent logger to drain first. */
    sleep(8);
    /* The diagnostic kernel's watchdog selects Recovery before resetting.
     * reboot(0) here would run this same boot_a image again and overwrite
     * the result with an incomplete next boot before the host can read it. */
    if (getpid() == 1) for (;;) sleep(1);
    exit(1);
}

static uint64_t usec(void)
{
    mach_timebase_info_data_t t;
    mach_timebase_info(&t);
    return mach_absolute_time() * t.numer / t.denom / 1000;
}

static GLuint shader(GLenum type, const char *source)
{
    GLuint s = glCreateShader(type);
    glShaderSource(s, 1, &source, NULL);
    glCompileShader(s);
    GLint good = 0;
    glGetShaderiv(s, GL_COMPILE_STATUS, &good);
    if (!good) {
        char log[2048]; glGetShaderInfoLog(s, sizeof(log), NULL, log);
        printf("SWEET GLES: shader: %s\n", log); fail("compile", type);
    }
    return s;
}

static void property(CFMutableDictionaryRef d, CFStringRef key, int value)
{
    CFNumberRef n = CFNumberCreate(NULL, kCFNumberIntType, &value);
    CFDictionarySetValue(d, key, n); CFRelease(n);
}

static void display_open(void)
{
    io_service_t s = IOServiceGetMatchingService(0, IOServiceMatching("IOMobileFramebuffer"));
    if (!s) fail("display missing", 0);
    kern_return_t kr = IOServiceOpen(s, mach_task_self(), 0, &fb);
    IOObjectRelease(s);
    if (kr) fail("display open", kr);
    uint64_t size[2]; uint32_t count = 2;
    kr = IOConnectCallScalarMethod(fb, 8, NULL, 0, size, &count);
    if (kr || count != 2 || !size[0] || !size[1] || size[0] > 4096 || size[1] > 4096)
        fail("display size", kr);
    width = (unsigned)size[0]; height = (unsigned)size[1];
    CFMutableDictionaryRef d = CFDictionaryCreateMutable(NULL, 0,
        &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    property(d, kIOSurfaceWidth, width); property(d, kIOSurfaceHeight, height);
    property(d, kIOSurfaceBytesPerElement, 4);
    property(d, kIOSurfaceBytesPerRow, width * 4);
    property(d, kIOSurfaceAllocSize, width * height * 4);
    property(d, kIOSurfacePixelFormat, 0x42475241); /* BGRA */
    surface = IOSurfaceCreate(d); CFRelease(d);
    if (!surface) fail("IOSurfaceCreate", 0);
    printf("SWEET GLES: surface=%u canvas=%ux%u stride=%zu\n", IOSurfaceGetID(surface),
        width, height, IOSurfaceGetBytesPerRow(surface));
}

static void put32(unsigned char *p, unsigned at, uint32_t n) { memcpy(p + at, &n, 4); }

static void present(unsigned frame)
{
    kern_return_t kr = IOSurfaceLock(surface, 0, NULL);
    if (kr) fail("surface lock", kr);
    unsigned char *base = IOSurfaceGetBaseAddress(surface);
    size_t stride = IOSurfaceGetBytesPerRow(surface);
    if (!base || stride < width * 4) fail("surface map", 0);
    /* GLES readback is bottom-up RGBA; display consumes top-down BGRA. */
    for (unsigned y = 0; y < height; y++) for (unsigned x = 0; x < width; x++) {
        const unsigned char *src = pixels + ((H - 1 - y * H / height) * W + x * W / width) * 4;
        unsigned char *dst = base + y * stride + x * 4;
        dst[0] = src[2]; dst[1] = src[1]; dst[2] = src[0]; dst[3] = src[3];
    }
    kr = IOSurfaceUnlock(surface, 0, NULL);
    if (kr) fail("surface unlock", kr);
    uint64_t swap = 0; uint32_t count = 1;
    kr = IOConnectCallScalarMethod(fb, 4, NULL, 0, &swap, &count);
    if (kr || count != 1) fail("swap begin", kr);
    unsigned char rec[0x46c] = {0};
    put32(rec, 0x50, swap); put32(rec, 0x54, IOSurfaceGetID(surface));
    put32(rec, 0x6c, width); put32(rec, 0x70, height);
    put32(rec, 0xcc, width); put32(rec, 0xd0, height); put32(rec, 0x104, 1);
    kr = IOConnectCallStructMethod(fb, 5, rec, sizeof(rec), NULL, NULL);
    if (kr) fail("swap end", kr);
    printf("SWEET GLES: frame=%u swap=%llu submitted\n", frame, swap);
    /* Existing display consumes latest swap on a timer. Keep the surface alive. */
    sleep(1);
}

static void expect(unsigned x, unsigned y, int r, int g, int b)
{
    const unsigned char *p = pixels + (y * W + x) * 4;
    printf("SWEET GLES: pixel %u,%u=%u,%u,%u,%u expected=%d,%d,%d\n",
        x, y, p[0], p[1], p[2], p[3], r, g, b);
    if (abs(p[0] - r) > 2 || abs(p[1] - g) > 2 || abs(p[2] - b) > 2)
        fail("pixel mismatch", x << 16 | y);
}

static void eagl_probe(void)
{
    void *apple = dlopen("/System/Library/Frameworks/OpenGLES.framework/OpenGLES", RTLD_NOW | RTLD_LOCAL);
    if (!apple) { printf("SWEET GLES: dlopen: %s\n", dlerror()); fail("OpenGLES", 0); }
    /* Record the real 20H392 dispatch stubs before replacing Objective-C methods.
     * The upstream slots describe 20F66: these bytes let us compare its ABI. */
    const char *names[] = { "glClear", "glClearColor", "glDrawArrays", "glFinish", "glGetError", "glReadPixels" };
    for (unsigned n = 0; n < sizeof(names) / sizeof(names[0]); n++) {
        const uint32_t *code = dlsym(apple, names[n]);
        if (!code) fail("Apple GL symbol", n);
        printf("SWEET GLES: Apple %s", names[n]);
        for (unsigned i = 0; i < 12; i++) printf(" %08x", code[i]);
        printf("\n");
    }
#ifndef SWEET_GLES_LIBRARY
#define SWEET_GLES_LIBRARY "/usr/local/sweet/lib/libsweet-gles.dylib"
#endif
    void *bridge = dlopen(SWEET_GLES_LIBRARY, RTLD_NOW | RTLD_LOCAL);
    if (!bridge) { printf("SWEET GLES: dlopen: %s\n", dlerror()); fail("EAGL bridge", 0); }
    Class cls = objc_getClass("EAGLContext");
    id object = ((id (*)(id, SEL))objc_msgSend)((id)cls, sel_registerName("alloc"));
    object = ((id (*)(id, SEL, unsigned long, id))objc_msgSend)(object,
        sel_registerName("initWithAPI:properties:"), 3, nil);
    if (!object) fail("EAGL API3", 0);
    void **table = ((void **(*)(id, SEL))objc_msgSend)(object, sel_registerName("getMacroContextPrivate"));
    if (!table || !table[0]) fail("EAGL macro table", 0);
    ((void (*)(void *, float, float, float, float))table[0x68 / 8])(table[0], .25f, .5f, .75f, 1);
    ((void (*)(void *, unsigned))table[0x58 / 8])(table[0], GL_COLOR_BUFFER_BIT);
    ((void (*)(void *))table[0x2d0 / 8])(table[0]);
    unsigned char pixel[4] = {0};
    ((void (*)(void *, int, int, int, int, unsigned, unsigned, void *))table[0x770 / 8])(
        table[0], 8, 8, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, pixel);
    unsigned error = ((unsigned (*)(void *))table[0x338 / 8])(table[0]);
    printf("SWEET GLES: EAGL API3 macro pixel=%u,%u,%u,%u error=0x%x\n",
        pixel[0], pixel[1], pixel[2], pixel[3], error);
    if (error || abs(pixel[0] - 64) > 2 || abs(pixel[1] - 128) > 2 || abs(pixel[2] - 191) > 2)
        fail("EAGL macro pixel", error);
    printf("SWEET GLES: EAGL bridge PASS\n");
    ((void (*)(id, SEL))objc_msgSend)(object, sel_registerName("release"));
}

int main(int argc, char **argv)
{
    (void)argc; (void)argv;
    int console = open("/dev/console", O_RDWR);
    if (console >= 0) { dup2(console, 1); dup2(console, 2); close(console); }
    setvbuf(stdout, NULL, _IONBF, 0);
    printf("SWEET GLES: begin hardware_required=%d pid=%d\n", SWEET_GLES_HARDWARE, getpid());
    const int attributes[] = { OSMESA_FORMAT, OSMESA_RGBA, OSMESA_PROFILE,
        OSMESA_ES_PROFILE, OSMESA_CONTEXT_MAJOR_VERSION, 2, 0 };
    OSMesaContext context = OSMesaCreateContextAttribs(attributes, NULL);
    if (!context || !OSMesaMakeCurrent(context, window, GL_UNSIGNED_BYTE, 16, 16))
        fail("context", 0);
    printf("SWEET GLES: renderer=%s version=%s vendor=%s\n",
        glGetString(GL_RENDERER), glGetString(GL_VERSION), glGetString(GL_VENDOR));
    const char *renderer = (const char *)glGetString(GL_RENDERER);
    if (SWEET_GLES_HARDWARE && (!renderer || !strstr(renderer, "G710") ||
            !strstr(renderer, "Panfrost"))) fail("hardware renderer required", 0);
    display_open();
    GLuint texture, framebuffer;
    glGenTextures(1, &texture); glBindTexture(GL_TEXTURE_2D, texture);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, W, H, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
    glGenFramebuffers(1, &framebuffer); glBindFramebuffer(GL_FRAMEBUFFER, framebuffer);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture, 0);
    if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) fail("FBO", 0);
    GLuint vs = shader(GL_VERTEX_SHADER, "attribute vec2 pos; void main(){gl_Position=vec4(pos,0.,1.);}");
    GLuint fs = shader(GL_FRAGMENT_SHADER, "precision mediump float; uniform vec4 color; void main(){gl_FragColor=color;}");
    GLuint program = glCreateProgram(); glAttachShader(program, vs); glAttachShader(program, fs);
    glBindAttribLocation(program, 0, "pos"); glLinkProgram(program);
    GLint linked; glGetProgramiv(program, GL_LINK_STATUS, &linked);
    if (!linked) fail("link", 0);
    glUseProgram(program); GLint color = glGetUniformLocation(program, "color");
    glViewport(0, 0, W, H); glDisable(GL_DITHER);
    const GLfloat vertices[] = { -.8f,-.8f, .8f,-.8f, 0.f,.8f };
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, vertices); glEnableVertexAttribArray(0);
    for (unsigned frame = 0; frame < 4; frame++) {
        uint64_t start = usec();
        glDisable(GL_BLEND); glClearColor(0, 0, 1, 1); glClear(GL_COLOR_BUFFER_BIT);
        if (frame == 2) { glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA); }
        glUniform4f(color, frame == 1 ? 0 : 1, frame == 1 ? 1 : 0, 0, frame == 2 ? .5f : 1);
        glDrawArrays(GL_TRIANGLES, 0, 3); glFinish();
        glReadPixels(0, 0, W, H, GL_RGBA, GL_UNSIGNED_BYTE, pixels);
        GLenum error = glGetError(); if (error) fail("draw/readback", error);
        printf("SWEET GLES: frame=%u render_readback_us=%llu\n", frame, usec() - start);
        expect(4, 4, 0, 0, 255);
        expect(128, 128, frame == 1 ? 0 : frame == 2 ? 128 : 255,
            frame == 1 ? 255 : 0, frame == 2 ? 127 : 0);
        present(frame);
    }
    eagl_probe();
    printf("SWEET GLES: PASS shaders=2 draws=4 pixel_checks=9 swaps=4 eagl_api=3 hardware_claim=%d\n",
        SWEET_GLES_HARDWARE);
    sleep(8);
    if (getpid() == 1) for (;;) sleep(1);
    CFRelease(surface); IOServiceClose(fb); OSMesaDestroyContext(context);
    return 0;
}
