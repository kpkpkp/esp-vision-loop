#include <stdlib.h>
#include <string.h>

#define LCD_H_RES       240
#define LCD_V_RES       240

#include "display_init.h"

void app_main(void) {
    display_init();

    /* Clear to WHITE first — instant visual confirmation that display works */
    display_clear(__builtin_bswap16(0xFFFF));

    /* Brief pause so the white screen is visible */
    vTaskDelay(pdMS_TO_TICKS(1000));

    /* Draw red circle efficiently: one row at a time via display_draw() */
    int cx = LCD_H_RES / 2;
    int cy = LCD_V_RES / 2;
    int r = 60;
    uint16_t black = __builtin_bswap16(0x0000);
    uint16_t red   = __builtin_bswap16(0xF800);

    /* Allocate a row buffer */
    uint16_t *row = heap_caps_malloc(LCD_H_RES * sizeof(uint16_t), MALLOC_CAP_DMA);
    if (!row) return;

    for (int y = 0; y < LCD_V_RES; y++) {
        for (int x = 0; x < LCD_H_RES; x++) {
            int dx = x - cx;
            int dy = y - cy;
            row[x] = (dx * dx + dy * dy <= r * r) ? red : black;
        }
        display_draw(0, y, LCD_H_RES, y + 1, row);
    }
    free(row);

    /* Keep alive */
    while (1) { vTaskDelay(pdMS_TO_TICKS(10000)); }
}
