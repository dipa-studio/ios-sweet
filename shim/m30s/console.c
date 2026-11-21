#include "console.h"
#include "font.h"

uintptr_t fb_base = 0;
uint32_t fb_width = 0, fb_height = 0, fb_stride = 0;
uint32_t cursor_x = 0, cursor_y = 0;
uint32_t char_w = 8, char_h = 16;

static inline void fb_write32(uintptr_t addr, uint32_t val)
{
	*(volatile uint32_t *)addr = val;
}

void con_init(uintptr_t base, uint32_t width, uint32_t height, uint32_t stride)
{
	fb_base = base;
	fb_width = width;
	fb_height = height;
	fb_stride = stride;
	cursor_x = 0;
	cursor_y = 0;
	con_clear(BLACK);
}

void con_clear(uint32_t color)
{
	if (!fb_base)
		return;
	uint32_t *fb = (uint32_t *)fb_base;
	for (uint32_t y = 0; y < fb_height; y++) {
		for (uint32_t x = 0; x < fb_width; x++) {
			fb[y * (fb_stride / 4) + x] = color;
		}
	}
	cursor_x = 0;
	cursor_y = 0;
}

static void con_scroll_up(void)
{
	if (!fb_base)
		return;
	uint32_t *fb = (uint32_t *)fb_base;
	uint32_t row_bytes = fb_stride;
	uint32_t bytes_per_row = fb_width * 4;
	uint32_t rows_to_move = fb_height - char_h;

	/* Move framebuffer up by one character row */
	for (uint32_t y = 0; y < rows_to_move; y++) {
		uint32_t *dst = (uint32_t *)((uintptr_t)fb + y * row_bytes);
		uint32_t *src = (uint32_t *)((uintptr_t)fb + (y + char_h) * row_bytes);
		for (uint32_t x = 0; x < fb_width; x++) {
			dst[x] = src[x];
		}
	}

	/* Clear the last character row */
	uint32_t *last_row = (uint32_t *)((uintptr_t)fb + rows_to_move * row_bytes);
	for (uint32_t y = 0; y < char_h; y++) {
		for (uint32_t x = 0; x < fb_width; x++) {
			last_row[y * (fb_stride / 4) + x] = BLACK;
		}
	}
	cursor_y = rows_to_move;
}

void con_putc(char c)
{
	if (!fb_base || c == '\0')
		return;

	if (c == '\n') {
		cursor_x = 0;
		cursor_y += char_h;
		if (cursor_y + char_h > fb_height)
			con_scroll_up();
		return;
	}

	if (c == '\r') {
		cursor_x = 0;
		return;
	}

	if (c == '\t') {
		cursor_x = (cursor_x + 8 * char_w) & ~(7 * char_w);
		if (cursor_x >= fb_width) {
			cursor_x = 0;
			cursor_y += char_h;
			if (cursor_y + char_h > fb_height)
				con_scroll_up();
		}
		return;
	}

	if ((unsigned char)c < 32 || (unsigned char)c >= 127)
		c = '?';

	const uint8_t *glyph = font8x16 + (c - 32) * 16;

	for (uint32_t row = 0; row < 16; row++) {
		uint8_t bits = glyph[row];
		uint32_t y = cursor_y + row;
		if (y >= fb_height)
			break;

		uint32_t *fb_row = (uint32_t *)((uintptr_t)fb_base + y * fb_stride + cursor_x * 4);

		for (uint32_t col = 0; col < 8; col++) {
			uint32_t x = cursor_x + col;
			if (x >= fb_width)
				break;
			fb_row[col] = (bits & (1 << (7 - col))) ? WHITE : BLACK;
		}
	}

	cursor_x += 8;
	if (cursor_x + 8 > fb_width) {
		cursor_x = 0;
		cursor_y += 16;
		if (cursor_y + 16 > fb_height)
			con_scroll_up();
	}
}

void con_puts(const char *s)
{
	while (*s)
		con_putc(*s++);
}

void con_hex(const char *label, uint64_t val)
{
	if (label)
		con_puts(label);
	char buf[17];
	for (int i = 15; i >= 0; i--) {
		uint8_t nib = val & 0xf;
		buf[15 - i] = nib < 10 ? '0' + nib : 'a' + nib - 10;
		val >>= 4;
	}
	buf[16] = '\0';
	con_puts("0x");
	con_puts(buf);
	con_putc('\n');
}

void con_hex2(const char *label, const char *l2, uint64_t v1, uint64_t v2)
{
	if (label)
		con_puts(label);
	con_hex("", v1);
	if (l2)
		con_puts(l2);
	con_hex("", v2);
}

void con_str(const char *label, const char *val)
{
	if (label)
		con_puts(label);
	if (val)
		con_puts(val);
	con_putc('\n');
}

void con_skip(void)
{
	con_putc('\n');
}