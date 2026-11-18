#pragma once
#include <stdint.h>

/*
 * Xiaomi Mi 8 (dipper, SDM845) bring-up diagnostic: dumps the display
 * pipeline ABL left behind, tries to push frames to the command-mode panel,
 * and logs everything into the ramoops console zone. Returns when done.
 */
void mi8_diag(uintptr_t dtb);
void mi8_touch_probe(void);
void mi8_touch_bringup(void);
void mi8_panic_log(const char *stage, uint64_t slot, uint64_t esr, uint64_t elr, uint64_t far);
