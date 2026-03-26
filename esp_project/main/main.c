#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_vendor.h"
#include "esp_lcd_panel_ops.h"
#include "esp_heap_caps.h"

/*  --- Configuration (filled by codegen from device.yaml) --- */
#define LCD_H_RES       240
#define LCD_V_RES       320
#define LCD_PIN_MOSI    23
#define LCD_PIN_SCLK    18
#define LCD_PIN_CS      5
#define LCD_PIN_DC      16
#define LCD_PIN_RST     17
#define LCD_SPI_FREQ_HZ (40 * 1000 * 1000)

/* --- Helper: fill a rectangular region with a color */
static void draw_circle(esp_lcd_panel_handle_t panel, int xc, int yc, int r, uint16_t color) {
    for (int x = -r; x <= r; ++x) {
        for (int y = -r; y <= r; ++y) {
            if ((x * x + y * y) <= (r * r)) {
                esp_lcd_panel_draw_pixel(panel, xc + x, yc + y, color);
            }
        }
    }
}

void app_main(void) {
    /* 1. Backlight GPIO */
    gpio_set_level((gpio_num_t)LCD_PIN_BK, 1);
    
    /* 2. SPI bus init */
    spi_bus_config_t bus_cfg = {
        .mosi_io_num = LCD_PIN_MOSI,
        .miso_io_num = -1,
        .sclk_io_num = LCD_PIN_SCLK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 4096,
    };
    spi_bus_initialize(HSPI_HOST, &bus_cfg, 1);
    
    /* 3. Panel IO (SPI) */
    esp_lcd_spi_io_config_t io = {
        .spi_host = HSPI_HOST,
        .dc_gpio_num = LCD_PIN_DC,
        .cs_gpio_num = LCD_PIN_CS,
        .reset_gpio_num = LCD_PIN_RST,
    };
    
    /* 4. Panel driver init (e.g., esp_lcd_new_panel_st7789) */
    const esp_lcd_panel_io_t io_conf = {
        .spi_io = &io,
        .type = LCD_PANEL_IO_SPI,
    };
    
    esp_lcd_panel_handle_t panel;
    esp_lcd_new_panel(&io_conf, &panel);
    
    /* 5. Reset + init + mirror/swap/invert as needed */
    esp_lcd_panel_init(panel);
    
    /* 6. Clear screen */
    esp_lcd_panel_clear(panel);
    
    /* 7. Draw the requested shape into pixel buffer */
    draw_circle(panel, LCD_H_RES / 2, LCD_V_RES / 2, LCD_H_RES / 4, 0xF800); // Red circle
    
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}