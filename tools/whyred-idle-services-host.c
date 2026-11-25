#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>

static unsigned int checks;
#define CHECK(x) do { checks++; if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); exit(1); } } while (0)
static unsigned int daif = 3, pending, waits, barriers, spurious;
static bool ml_get_interrupts_enabled(void) { return daif != 3; }
static bool cpu_interrupt_is_pending(void) { return pending != 0; }
static void mock_dsb(unsigned int scope) { CHECK(scope == 15); barriers++; }
static void mock_wfi(void)
{
    CHECK(daif == 3); /* No handler may use the interrupt-stack top here. */
    CHECK(barriers == waits + 1);
    waits++;
    if (waits > spurious) pending = 1;
    CHECK(waits <= 17);
}
#define DSB_SY 15
#define __builtin_arm_dsb mock_dsb
#define __builtin_arm_wfi mock_wfi
/* ACTUAL IDLE HELPER */

struct proc { const char *p_name; int pid; };
typedef struct proc *proc_t;
#define PROC_NULL NULL
static unsigned int boot_value, boot_present, log_count;
static char last_log[512];
static pthread_mutex_t log_lock = PTHREAD_MUTEX_INITIALIZER;
static int PE_parse_boot_argn(const char *name, void *value, unsigned int size)
{
    assert(strcmp(name, "whyred-service-trace") == 0 && size == sizeof(uint32_t));
    *(uint32_t *)value = boot_value;
    return boot_present;
}
static int proc_getpid(proc_t p) { return p->pid; }
static unsigned long long mach_absolute_time(void) { return 0x12345678ULL; }
static void service_printf(const char *fmt, ...)
{
    pthread_mutex_lock(&log_lock);
    va_list ap; va_start(ap, fmt);
    int n = vsnprintf(last_log, sizeof(last_log), fmt, ap);
    va_end(ap);
    assert(n > 0 && (unsigned int)n < sizeof(last_log));
    log_count++;
    pthread_mutex_unlock(&log_lock);
}
#define printf service_printf
#define relaxed __ATOMIC_RELAXED
#define os_atomic_load(p, order) __atomic_load_n((p), (order))
static bool host_cmpxchg(uint32_t *p, uint32_t old, uint32_t new_value)
{
    return __atomic_compare_exchange_n(p, &old, new_value, false, __ATOMIC_RELAXED, __ATOMIC_RELAXED);
}
#define os_atomic_cmpxchg(p, old, new_value, order) host_cmpxchg((p), (old), (new_value))
/* ACTUAL SERVICE HELPER */
#undef printf

static void *race_report(void *opaque)
{
    proc_t p = opaque;
    for (unsigned int i = 0; i < 1000; i++)
        whyred_service_event(p, WHYRED_SERVICE_EXIT, 0, 0, 0xb, 2, 11);
    return NULL;
}

int main(void)
{
    for (unsigned int early = 0; early < 2; early++) {
        for (unsigned int s = 0; s <= 16; s++) {
            daif = 3; pending = early; waits = barriers = 0; spurious = s;
            CHECK(whyred_idle_wait_pending());
            CHECK(daif == 3 && pending == 1);
            CHECK(waits == (early ? 0 : s + 1));
            CHECK(barriers == waits);
        }
    }
    struct proc p = { "bluetoothd", 82 };
    for (unsigned int mode = 0; mode < 4; mode++) {
        boot_present = mode != 0; boot_value = mode == 3 ? 2 : 0;
        whyred_service_event(&p, WHYRED_SERVICE_EXEC, 0, 1, 0, 0, 0);
    }
    CHECK(log_count == 0);
    boot_present = boot_value = 1;
    whyred_service_event(NULL, WHYRED_SERVICE_EXEC, 0, 1, 0, 0, 0);
    whyred_service_event(&p, WHYRED_SERVICE_EVENTS, 0, 1, 0, 0, 0);
    CHECK(log_count == 0);
    const char *reject[] = { "", "xpcproxy", "bluetoothdX", "fairplayd", "suggestd/helper", "pkdX" };
    for (unsigned int i = 0; i < sizeof(reject)/sizeof(reject[0]); i++) {
        p.p_name = reject[i];
        whyred_service_event(&p, WHYRED_SERVICE_EXEC, 0, 1, 0, 0, 0);
        CHECK(log_count == 0);
    }
    const char *targets[] = { "bluetoothd", "fairplayd.H2", "suggestd", "lsd", "pkd" };
    for (unsigned int i = 0; i < 5; i++) {
        p.p_name = targets[i];
        whyred_service_event(&p, WHYRED_SERVICE_EXEC, 13, 0, 0, 0, 0);
        CHECK(log_count == i + 1);
        CHECK(strstr(last_log, targets[i]) != NULL);
        CHECK(strstr(last_log, "pid=82 event=exec seq=1 error=13 detail=0") != NULL);
        CHECK(strstr(last_log, "ticks=305419896") != NULL);
    }
    p.p_name = "suggestd";
    whyred_service_event(&p, WHYRED_SERVICE_SPAWN, 0, 1, 0, 0, 0);
    CHECK(strstr(last_log, "event=spawn seq=1 error=0 detail=1") != NULL);
    whyred_service_event(&p, WHYRED_SERVICE_EXIT, 0, 0, 0x100, 0, 0);
    CHECK(strstr(last_log, "event=exit seq=1 error=0 detail=0 status=0x100 reason=0/0x0") != NULL);
    p.p_name = "fairplayd.H2";
    whyred_service_event(&p, WHYRED_SERVICE_EXIT, 0, 1, 0x86, 2, UINT64_MAX);
    CHECK(strstr(last_log, "detail=1 status=0x86 reason=2/0xffffffffffffffff") != NULL);
    unsigned int before = log_count;
    p.p_name = "bluetoothd";
    for (unsigned int i = 0; i < 1000; i++)
        whyred_service_event(&p, WHYRED_SERVICE_EXEC, 0, 1, 0, 0, 0);
    CHECK(log_count == before + 63);
    CHECK(strstr(last_log, "seq=64") != NULL);
    before = log_count;
    p.p_name = "pkd";
    pthread_t workers[8];
    for (unsigned int i = 0; i < 8; i++) CHECK(pthread_create(&workers[i], NULL, race_report, &p) == 0);
    for (unsigned int i = 0; i < 8; i++) CHECK(pthread_join(workers[i], NULL) == 0);
    CHECK(log_count == before + 64);
    CHECK(strstr(last_log, "status=0xb reason=2/0xb") != NULL);
    printf("{\"checks\":%u,\"idle_scenarios\":34,\"concurrent_report_attempts\":8000}\n", checks);
    return 0;
}
