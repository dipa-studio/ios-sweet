#pragma once
/* Just enough of the XNU environment to compile and unit-test mi8/xnu/mi8_touch.c on a PC (-DMI8_TOUCH_HOST). */
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
typedef unsigned long vm_offset_t;
typedef unsigned long vm_size_t;
typedef int kern_return_t;
typedef void *thread_t;
typedef int wait_result_t;
extern uint32_t host_mmio_rd(vm_offset_t addr);
extern void host_mmio_wr(vm_offset_t addr, uint32_t v);
extern void host_delay_us(unsigned us);
#define NSEC_PER_USEC 1000u
#define NSEC_PER_MSEC 1000000u
static inline void delay_for_interval(uint32_t interval, uint32_t scale) { (void)scale; host_delay_us(interval); }
