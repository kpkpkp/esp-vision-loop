/*
 * draw_api.h — Minimal API for LLM-generated drawing code
 *
 * This header provides ONLY what draw_frame() needs. The full ESP-IDF
 * framework (display init, SPI, FreeRTOS) is pre-compiled in the build kit.
 * Only this file + draw_frame.c are compiled on-device.
 */
#pragma once

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

/* Display dimensions — Waveshare ESP32-S3-LCD-1.28 (GC9A01 round) */
#define LCD_H_RES 240
#define LCD_V_RES 240

/* heap_caps_malloc flags */
#define MALLOC_CAP_DMA (1 << 2)

/* FreeRTOS delay — CONFIG_FREERTOS_HZ=1000 so 1 tick = 1ms */
#define pdMS_TO_TICKS(ms) ((uint32_t)(ms))

/*
 * Draw a rectangular block of pixels to the display.
 * color_data: RGB565 (byte-swapped for GC9A01), row-major.
 * Size = (x_end - x_start) * (y_end - y_start) pixels.
 */
extern void display_draw(int x_start, int y_start, int x_end, int y_end,
                         const uint16_t *color_data);

/* Fill entire screen with one RGB565 color (already byte-swapped). */
extern void display_clear(uint16_t color);

/* Allocate DMA-capable memory. Use MALLOC_CAP_DMA for display buffers. */
extern void *heap_caps_malloc(size_t size, uint32_t caps);

/* FreeRTOS delay. Use pdMS_TO_TICKS(ms) for the argument. */
extern void vTaskDelay(uint32_t ticks);

/*
 * Byte-swap helper for RGB565 colors.
 * ESP32-S3 is little-endian; GC9A01 SPI expects big-endian RGB565.
 * Use this for ALL color constants: __builtin_bswap16(0xF800) = red.
 *
 * Common colors (already swapped):
 *   Red:     __builtin_bswap16(0xF800)
 *   Green:   __builtin_bswap16(0x07E0)
 *   Blue:    __builtin_bswap16(0x001F)
 *   White:   __builtin_bswap16(0xFFFF)
 *   Black:   __builtin_bswap16(0x0000)
 *   Yellow:  __builtin_bswap16(0xFFE0)
 *   Cyan:    __builtin_bswap16(0x07FF)
 *   Magenta: __builtin_bswap16(0xF81F)
 *   Orange:  __builtin_bswap16(0xFD20)
 */

/* ── BLE scene interface (set by main.c BLE GATT callbacks) ── */
#define BLE_SCENE_BUF_SIZE 512
extern volatile uint8_t ble_scene_buf[BLE_SCENE_BUF_SIZE];
extern volatile int ble_scene_len;
extern volatile int ble_scene_ready;

/* Set display backlight brightness (0–100%). Implemented in main.c via LEDC PWM. */
extern void display_set_brightness(int percent);
