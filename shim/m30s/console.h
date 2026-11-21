#ifndef CONSOLE_H
#define CONSOLE_H

#include <stdint.h>

/* Framebuffer colors (BGRA8888) */
#define RED     0xff0000ffUL
#define GREEN   0xff00ff00UL
#define BLUE    0xffff0000UL
#define WHITE   0xffffffffUL
#define BLACK   0xff000000UL
#define YELLOW  0xff00ffffUL
#define CYAN    0xffffff00UL
#define MAGENTA 0xffff00ffUL

extern uintptr_t fb_base;
extern uint32_t fb_width, fb_height, fb_stride;
extern uint32_t cursor_x, cursor_y;
extern uint32_t char_w, char_h;

void con_init(uintptr_t base, uint32_t width, uint32_t height, uint32_t stride);
void con_clear(uint32_t color);
void con_putc(char c);
void con_puts(const char *s);
void con_hex(const char *label, uint64_t val);
void con_hex2(const char *label, const char *l2, uint64_t v1, uint64_t v2);
void con_str(const char *label, const char *val);
void con_skip(void);

#endif