#include <stdlib.h>
#include <string.h>
#include <math.h>

#define LCD_H_RES       240
#define LCD_V_RES       320
#define LCD_PIN_MOSI    23
#define LCD_PIN_SCLK    18
#define LCD_PIN_CS      5
#define LCD_PIN_DC      16
#define LCD_PIN_RST     17
#define LCD_PIN_BK      4
#define LCD_SPI_FREQ_HZ (40 * 1000 * 1000)

#include "display_init.h"

void app_main(void) {
    display_init();
    display_clear(0xFFFF); // Clear screen to white
    
    int centerX = LCD_H_RES / 2;
    int centerY = LCD_V_RES / 2;
    int radius = 50;
    uint16_t color = 0xF800; // Red in RGB565 format

    for (int y = 0; y < LCD_V_RES; ++y) {
        for (int x = 0; x < LCD_H_RES; ++x) {
            int dx = centerX - x;
            int dy = centerY - y;
            if ((dx * dx + dy * dy) <= radius * radius) {
                display_draw(x, y, x, y, color); // Draw the pixel
            }
        }
    }
}