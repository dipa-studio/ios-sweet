/* clock_gettime equivalent for the Windows host parser tests. */
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <time.h>
#include <stdint.h>
#ifndef CLOCK_MONOTONIC
#define CLOCK_MONOTONIC 1
static int clock_gettime(int clock, struct timespec *ts) {
    LARGE_INTEGER ticks, frequency;
    (void)clock;
    QueryPerformanceCounter(&ticks);
    QueryPerformanceFrequency(&frequency);
    ts->tv_sec = (time_t)(ticks.QuadPart / frequency.QuadPart);
    ts->tv_nsec = (long)((ticks.QuadPart % frequency.QuadPart) * 1000000000 / frequency.QuadPart);
    return 0;
}
#endif
#ifndef ENOATTR
#define ENOATTR ENODATA
#endif
