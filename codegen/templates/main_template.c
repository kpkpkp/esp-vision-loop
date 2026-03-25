/*
 * ESP-IDF Display Drawing Template
 *
 * This is a reference skeleton for the LLM code generator.
 * The coding model uses this as structural guidance when generating main.c.
 *
 * Target: ESP32 with SPI/I2C display via esp_lcd APIs
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_vendor.h"
#include "esp_lcd_panel_ops.h"
#include "esp_heap_caps.h"
#include "esp_log.h"

static const char *TAG = "display_draw";

/* --- Configuration (filled by codegen from device.yaml) --- */
#define LCD_H_RES       240
#define LCD_V_RES       320
#define LCD_PIN_MOSI    23
#define LCD_PIN_SCLK    18
#define LCD_PIN_CS      5
#define LCD_PIN_DC      16
#define LCD_PIN_RST     17
#define LCD_PIN_BK      4
#define LCD_SPI_FREQ_HZ (40 * 1000 * 1000)

/* --- Helper: fill a rectangular region with a color --- */
static void fill_rect(esp_lcd_panel_handle_t panel,
                      int x0, int y0, int x1, int y1,
                      uint16_t color)
{
    int w = x1 - x0;
    int h = y1 - y0;
    size_t buf_size = w * sizeof(uint16_t);
    uint16_t *line = heap_caps_malloc(buf_size, MALLOC_CAP_DMA);
    for (int i = 0; i < w; i++) line[i] = color;
    for (int row = y0; row < y1; row++) {
        esp_lcd_panel_draw_bitmap(panel, x0, row, x1, row + 1, line);
    }
    free(line);
}

void app_main(void)
{
    /* 1. Backlight GPIO */
    /* 2. SPI bus init */
    /* 3. Panel IO (SPI) */
    /* 4. Panel driver init (e.g., esp_lcd_new_panel_st7789) */
    /* 5. Reset + init + mirror/swap/invert as needed */
    /* 6. Clear screen */
    /* 7. Draw the requested shape into pixel buffer */
    /* 8. esp_lcd_panel_draw_bitmap() */

    /* Keep display alive */
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
