/* Host test adapter for Git for Windows' zlib1.dll; never used by the kernel. */
#ifndef WHYRED_HOST_ZLIB_H
#define WHYRED_HOST_ZLIB_H
#include <windows.h>
#include <stdlib.h>
typedef unsigned char Bytef;
typedef unsigned int uInt;
typedef unsigned long uLong;
typedef void *voidpf;
typedef struct z_stream_s {
    Bytef *next_in; uInt avail_in; uLong total_in;
    Bytef *next_out; uInt avail_out; uLong total_out;
    char *msg; void *state;
    voidpf (*zalloc)(voidpf, uInt, uInt);
    void (*zfree)(voidpf, voidpf);
    voidpf opaque; int data_type; uLong adler; uLong reserved;
} z_stream;
#define Z_NULL 0
#define Z_OK 0
#define Z_STREAM_END 1
#define Z_FINISH 4
#define Z_BUF_ERROR (-5)
static HMODULE whyred_zlib(void) {
    static HMODULE dll;
    if (!dll) dll = LoadLibraryA("C:\\Program Files\\Git\\mingw64\\bin\\zlib1.dll");
    if (!dll) abort();
    return dll;
}
static int inflate_init(z_stream *s) {
    HMODULE dll = whyred_zlib();
    const char *(*version)(void) = (void *)GetProcAddress(dll, "zlibVersion");
    int (*init)(z_stream *, const char *, int) = (void *)GetProcAddress(dll, "inflateInit_");
    if (!version || !init) abort();
    return init(s, version(), sizeof(*s));
}
#define inflateInit(s) inflate_init(s)
static int inflate(z_stream *s, int mode) {
    int (*fn)(z_stream *, int) = (void *)GetProcAddress(whyred_zlib(), "inflate");
    if (!fn) abort();
    return fn(s, mode);
}
static int inflateEnd(z_stream *s) {
    int (*fn)(z_stream *) = (void *)GetProcAddress(whyred_zlib(), "inflateEnd");
    if (!fn) abort();
    return fn(s);
}
#endif
