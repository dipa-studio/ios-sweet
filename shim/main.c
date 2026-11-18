
#include <stdint.h>
#include "console.h"

/* MediaTek watchdog */
#define WDT_BASE       0x10007000UL
#define WDT_RST        (*(volatile uint32_t *)(WDT_BASE + 0x08))
#define WDT_RELOAD     0x1971u

/* ARM exception-level configuration */
#define HCR_EL2_RW     (1ULL << 31)
#define SPSR_EL1H      0x3C5ULL

#define EL1_STACK_SIZE 16384

struct boot_state {
    uint64_t x0, x1, x2, x3;
    uint64_t initial_sp;
    uint64_t current_el;
    uint64_t daif;
};

volatile struct boot_state boot_state = {0};

static uint8_t el1_stack[EL1_STACK_SIZE]
    __attribute__((aligned(16)));

static uint64_t timer_frequency;
static uint64_t last_ping;

/* Symbols supplied by the assembly below. */
extern char el1_vectors[];

__attribute__((noreturn))
void minimal_el1_main(void);

/* -------------------------------------------------------
 * Generic timer
 * ------------------------------------------------------- */

static inline uint64_t read_counter(void)
{
    uint64_t value;

    __asm__ volatile(
        "mrs %0, cntpct_el0"
        : "=r"(value)
    );

    return value;
}

static inline uint64_t read_frequency(void)
{
    uint64_t value;

    __asm__ volatile(
        "mrs %0, cntfrq_el0"
        : "=r"(value)
    );

    return value;
}

/* -------------------------------------------------------
 * Watchdog
 * ------------------------------------------------------- */

static void watchdog_service(void)
{
    uint64_t now = read_counter();

    if (now - last_ping >= timer_frequency)
    {
        WDT_RST = WDT_RELOAD;

        __asm__ volatile("dsb sy");

        last_ping = now;
    }
}

static void watchdog_start(void)
{
    timer_frequency = read_frequency();

    last_ping = read_counter();

    WDT_RST = WDT_RELOAD;

    __asm__ volatile("dsb sy");
}

/* -------------------------------------------------------
 * EL1 exception vectors
 *
 * 16 entries, 128 bytes each.
 * Every exception enters an infinite loop.
 * ------------------------------------------------------- */

__asm__(
    ".section .text.el1vectors, \"ax\"\n"
    ".balign 2048\n"

    ".global el1_vectors\n"
    "el1_vectors:\n"

    ".rept 16\n"
    "    b el1_exception\n"
    "    .space 124\n"
    ".endr\n"

    "el1_exception:\n"
    "    b el1_exception\n"

    ".previous\n"
);

/* -------------------------------------------------------
 * EL2 -> EL1 transition
 * ------------------------------------------------------- */

__attribute__((noreturn, noinline))
static void enter_el1(void)
{
    uint64_t hcr;
    uint64_t stack_top;
    uint64_t vector_address;
    uint64_t entry_address;

    stack_top =
        (uint64_t)(el1_stack + sizeof(el1_stack));

    vector_address = (uint64_t)el1_vectors;
    entry_address = (uint64_t)minimal_el1_main;

    /* Read and preserve existing HCR_EL2 configuration. */
    __asm__ volatile(
        "mrs %0, hcr_el2"
        : "=r"(hcr)
    );

    /* EL1 must execute AArch64 instructions. */
    hcr |= HCR_EL2_RW;

    /*
     * Set up the return state:
     *
     * SPSR_EL2 = 0x3C5
     *   EL1h
     *   IRQ masked
     *   FIQ masked
     *   SError masked
     *   Debug exceptions masked
     */

    __asm__ volatile(
        "msr sp_el1, %0\n"
        "msr vbar_el1, %1\n"
        "msr hcr_el2, %2\n"
        "dsb sy\n"
        "isb\n"
        "msr elr_el2, %3\n"
        "msr spsr_el2, %4\n"
        "isb\n"
        "eret\n"

        :
        : "r"(stack_top),
          "r"(vector_address),
          "r"(hcr),
          "r"(entry_address),
          "r"(SPSR_EL1H)
        : "memory"
    );

    __builtin_unreachable();
}

/* -------------------------------------------------------
 * EL1 entry point
 * ------------------------------------------------------- */

__attribute__((noreturn))
void minimal_el1_main(void)
{
    uint64_t current_el;
    uint64_t sctlr;
    uint64_t vbar;

    __asm__ volatile(
        "mrs %0, CurrentEL"
        : "=r"(current_el)
    );

    __asm__ volatile(
        "mrs %0, sctlr_el1"
        : "=r"(sctlr)
    );

    __asm__ volatile(
        "mrs %0, vbar_el1"
        : "=r"(vbar)
    );

    con_str("ANGELICAN", "EL1 ENTERED");

    con_hex("CurrentEL", current_el);
    con_hex("SCTLR_EL1", sctlr);
    con_hex("VBAR_EL1", vbar);

    if (current_el != 0x4)
    {
        con_str("ERROR", "NOT RUNNING AT EL1");

        for (;;)
            watchdog_service();
    }

    if (sctlr & 1)
    {
        con_str("ERROR", "EL1 MMU ENABLED");

        for (;;)
            watchdog_service();
    }

    if (vbar != (uint64_t)el1_vectors)
    {
        con_str("ERROR", "INVALID EL1 VBAR");

        for (;;)
            watchdog_service();
    }

    con_str("STATUS", "EL1 RUNNING");
    con_str("MMU", "DISABLED");
    con_str("WATCHDOG", "ACTIVE");

    for (;;)
    {
        watchdog_service();
    }
}

/* -------------------------------------------------------
 * Original EL2 entry point
 * ------------------------------------------------------- */

__attribute__((noreturn))
void minimal_main(void)
{
    uint64_t current_el;
    uint64_t sctlr;
    uint64_t hcr;

    __asm__ volatile(
        "mrs %0, CurrentEL"
        : "=r"(current_el)
    );

    __asm__ volatile(
        "mrs %0, sctlr_el2"
        : "=r"(sctlr)
    );

    __asm__ volatile(
        "mrs %0, hcr_el2"
        : "=r"(hcr)
    );

    con_str("ANGELICAN", "EL2 INITIALIZED");

    con_hex("CurrentEL", current_el);
    con_hex("SCTLR_EL2", sctlr);
    con_hex("HCR_EL2", hcr);

    if (current_el != 0x8)
    {
        con_str("ERROR", "EXPECTED EL2");

        for (;;)
            ;
    }

    if (sctlr & 1)
    {
        con_str("ERROR", "EL2 MMU ENABLED");

        for (;;)
            ;
    }

    watchdog_start();

    if (!timer_frequency)
    {
        con_str("ERROR", "INVALID TIMER");

        for (;;)
            ;
    }

    con_str("TRANSITION", "PREPARING EL1");

    enter_el1();
}
