/*
 * display_init.h — GC9A01 240x240 round display on Waveshare ESP32-S3-LCD-1.28
 *
 * This file handles all ESP-IDF boilerplate: SPI bus, panel IO, GC9A01 driver.
 * The LLM-generated code only needs to #include this and call draw functions.
 *
 * Display config is set via #defines before including this file.
 */

#pragma once

#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_vendor.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_gc9a01.h"
#include "esp_heap_caps.h"
#include "esp_log.h"

/* Pin definitions — Waveshare ESP32-S3-LCD-1.28-B */
#ifndef LCD_H_RES
#define LCD_H_RES       240
#endif
#ifndef LCD_V_RES
#define LCD_V_RES       240
#endif
#define LCD_PIN_SCK     10
#define LCD_PIN_MOSI    11
#define LCD_PIN_CS      9
#define LCD_PIN_DC      8
#define LCD_PIN_RST     12
#define LCD_PIN_BK      40
#define LCD_SPI_FREQ_HZ (20 * 1000 * 1000)

static const char *TAG = "display";

static esp_lcd_panel_handle_t g_panel = NULL;

/**
 * Initialize the SPI bus, panel IO, and GC9A01 driver.
 * After this, g_panel is ready for esp_lcd_panel_draw_bitmap().
 */
static void display_init(void)
{
    /* Backlight — simple GPIO on (no PWM needed for demo) */
    gpio_config_t bk_cfg = {
        .pin_bit_mask = 1ULL << LCD_PIN_BK,
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&bk_cfg);
    gpio_set_level(LCD_PIN_BK, 1);

    /* SPI bus */
    spi_bus_config_t bus_cfg = {
        .mosi_io_num = LCD_PIN_MOSI,
        .miso_io_num = -1,
        .sclk_io_num = LCD_PIN_SCK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = LCD_H_RES * LCD_V_RES * sizeof(uint16_t),
    };
    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &bus_cfg, SPI_DMA_CH_AUTO));

    /* Panel IO */
    esp_lcd_panel_io_handle_t io_handle = NULL;
    esp_lcd_panel_io_spi_config_t io_config = {
        .dc_gpio_num = LCD_PIN_DC,
        .cs_gpio_num = LCD_PIN_CS,
        .pclk_hz = LCD_SPI_FREQ_HZ,
        .lcd_cmd_bits = 8,
        .lcd_param_bits = 8,
        .spi_mode = 0,
        .trans_queue_depth = 10,
    };
    ESP_ERROR_CHECK(esp_lcd_new_panel_io_spi(SPI2_HOST, &io_config, &io_handle));

    /* GC9A01 panel driver */
    esp_lcd_panel_dev_config_t panel_config = {
        .reset_gpio_num = LCD_PIN_RST,
        .rgb_ele_order = LCD_RGB_ELEMENT_ORDER_BGR,
        .bits_per_pixel = 16,
    };
    ESP_ERROR_CHECK(esp_lcd_new_panel_gc9a01(io_handle, &panel_config, &g_panel));

    /* Init sequence */
    ESP_ERROR_CHECK(esp_lcd_panel_reset(g_panel));
    ESP_ERROR_CHECK(esp_lcd_panel_init(g_panel));
    ESP_ERROR_CHECK(esp_lcd_panel_invert_color(g_panel, true));
    ESP_ERROR_CHECK(esp_lcd_panel_disp_on_off(g_panel, true));

    ESP_LOGI(TAG, "GC9A01 display initialized: %dx%d", LCD_H_RES, LCD_V_RES);
}

/**
 * Fill the entire screen with a single color (RGB565, byte-swapped for GC9A01).
 */
static void display_clear(uint16_t color)
{
    /* Byte-swap: ESP32-S3 is little-endian, GC9A01 SPI expects big-endian RGB565 */
    uint16_t swapped = __builtin_bswap16(color);
    int buf_lines = 20;
    size_t buf_size = LCD_H_RES * buf_lines * sizeof(uint16_t);
    uint16_t *buf = heap_caps_malloc(buf_size, MALLOC_CAP_DMA);
    if (!buf) {
        ESP_LOGE(TAG, "Failed to allocate clear buffer");
        return;
    }
    for (int i = 0; i < LCD_H_RES * buf_lines; i++) {
        buf[i] = swapped;
    }
    for (int y = 0; y < LCD_V_RES; y += buf_lines) {
        int end_y = y + buf_lines;
        if (end_y > LCD_V_RES) end_y = LCD_V_RES;
        esp_lcd_panel_draw_bitmap(g_panel, 0, y, LCD_H_RES, end_y, buf);
    }
    free(buf);
}

/**
 * Draw a rectangular block of pixels. color_data is RGB565 (byte-swapped),
 * row-major, size = (x_end - x_start) * (y_end - y_start) pixels.
 */
static void display_draw(int x_start, int y_start, int x_end, int y_end,
                         const uint16_t *color_data)
{
    esp_lcd_panel_draw_bitmap(g_panel, x_start, y_start, x_end, y_end, color_data);
}
