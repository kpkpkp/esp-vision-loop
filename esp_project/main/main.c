#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#define LCD_H_RES       240
#define LCD_V_RES       240

#include "display_init.h"
#include "esp_log.h"
#include "driver/ledc.h"

/* BLE includes */
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/util/util.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

#define MAIN_TAG "main"

/* ── Shared BLE→draw_frame scene buffer ───────────────────── */
#define BLE_SCENE_BUF_SIZE 512
volatile uint8_t ble_scene_buf[BLE_SCENE_BUF_SIZE];
volatile int ble_scene_len = 0;
volatile int ble_scene_ready = 0;

/* ── Backlight PWM via LEDC ───────────────────────────────── */
/* Waveshare ESP32-S3-LCD-1.28: backlight on GPIO2 */
#define BL_GPIO     2
#define BL_CHANNEL  LEDC_CHANNEL_0
#define BL_TIMER    LEDC_TIMER_0

static void backlight_init(void) {
    ledc_timer_config_t timer_cfg = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .timer_num = BL_TIMER,
        .duty_resolution = LEDC_TIMER_8_BIT,
        .freq_hz = 5000,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ledc_timer_config(&timer_cfg);

    ledc_channel_config_t ch_cfg = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = BL_CHANNEL,
        .timer_sel = BL_TIMER,
        .gpio_num = BL_GPIO,
        .duty = 255,  /* 100% initially */
        .hpoint = 0,
    };
    ledc_channel_config(&ch_cfg);
    ESP_LOGI(MAIN_TAG, "Backlight PWM initialized on GPIO%d", BL_GPIO);
}

void display_set_brightness(int percent) {
    if (percent < 0) percent = 0;
    if (percent > 100) percent = 100;
    uint32_t duty = (percent * 255) / 100;
    ledc_set_duty(LEDC_LOW_SPEED_MODE, BL_CHANNEL, duty);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, BL_CHANNEL);
}

/* ── BLE GATT ─────────────────────────────────────────────── */
/* Nordic UART base: 6E40xxxx-B5A3-F393-E0A9-E50E24DCCA9E */
static const ble_uuid128_t svc_uuid = BLE_UUID128_INIT(
    0x9E, 0xCA, 0xDC, 0x24, 0x0E, 0xE5, 0xA9, 0xE0,
    0x93, 0xF3, 0xA3, 0xB5, 0x01, 0x00, 0x40, 0x6E);
static const ble_uuid128_t scene_chr_uuid = BLE_UUID128_INIT(
    0x9E, 0xCA, 0xDC, 0x24, 0x0E, 0xE5, 0xA9, 0xE0,
    0x93, 0xF3, 0xA3, 0xB5, 0x08, 0x00, 0x40, 0x6E);
static const ble_uuid128_t bright_chr_uuid = BLE_UUID128_INIT(
    0x9E, 0xCA, 0xDC, 0x24, 0x0E, 0xE5, 0xA9, 0xE0,
    0x93, 0xF3, 0xA3, 0xB5, 0x09, 0x00, 0x40, 0x6E);

static int scene_write_cb(uint16_t conn_handle, uint16_t attr_handle,
                          struct ble_gatt_access_ctxt *ctxt, void *arg) {
    int len = OS_MBUF_PKTLEN(ctxt->om);
    if (len > 0 && len <= BLE_SCENE_BUF_SIZE) {
        ble_hs_mbuf_to_flat(ctxt->om, (void *)ble_scene_buf, len, NULL);
        ble_scene_len = len;
        ble_scene_ready = 1;
        ESP_LOGI(MAIN_TAG, "BLE scene: %d bytes", len);
    }
    return 0;
}

static int bright_write_cb(uint16_t conn_handle, uint16_t attr_handle,
                           struct ble_gatt_access_ctxt *ctxt, void *arg) {
    uint8_t val = 0;
    if (OS_MBUF_PKTLEN(ctxt->om) >= 1) {
        ble_hs_mbuf_to_flat(ctxt->om, &val, 1, NULL);
        display_set_brightness(val);
        ESP_LOGI(MAIN_TAG, "BLE brightness: %d%%", val);
    }
    return 0;
}

static const struct ble_gatt_svc_def gatt_svr_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = &svc_uuid.u,
        .characteristics = (struct ble_gatt_chr_def[]){
            {
                .uuid = &scene_chr_uuid.u,
                .access_cb = scene_write_cb,
                .flags = BLE_GATT_CHR_F_WRITE,
            },
            {
                .uuid = &bright_chr_uuid.u,
                .access_cb = bright_write_cb,
                .flags = BLE_GATT_CHR_F_WRITE,
            },
            { 0 },
        },
    },
    { 0 },
};

static void ble_advertise(void);

static void ble_on_sync(void) {
    ble_hs_id_infer_auto(0, NULL);
    ble_advertise();
    ESP_LOGI(MAIN_TAG, "BLE advertising as WM-ESP32");
}

static void ble_advertise(void) {
    struct ble_gap_adv_params adv_params = {
        .conn_mode = BLE_GAP_CONN_MODE_UND,
        .disc_mode = BLE_GAP_DISC_MODE_GEN,
    };

    struct ble_hs_adv_fields fields = {0};
    fields.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    fields.name = (const uint8_t *)"WM-ESP32";
    fields.name_len = 8;
    fields.name_is_complete = 1;
    fields.uuids128 = &svc_uuid;
    fields.num_uuids128 = 1;
    fields.uuids128_is_complete = 1;

    ble_gap_adv_set_fields(&fields);
    ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER, &adv_params, NULL, NULL);
}

static void ble_on_reset(int reason) {
    ESP_LOGW(MAIN_TAG, "BLE reset: reason=%d", reason);
}

static void ble_host_task(void *param) {
    nimble_port_run();
    nimble_port_freertos_deinit();
}

static void ble_init(void) {
    ESP_ERROR_CHECK(nimble_port_init());

    ble_hs_cfg.sync_cb = ble_on_sync;
    ble_hs_cfg.reset_cb = ble_on_reset;

    ble_svc_gap_init();
    ble_svc_gatt_init();
    ble_svc_gap_device_name_set("WM-ESP32");

    int rc = ble_gatts_count_cfg(gatt_svr_svcs);
    assert(rc == 0);
    rc = ble_gatts_add_svcs(gatt_svr_svcs);
    assert(rc == 0);

    nimble_port_freertos_init(ble_host_task);
    ESP_LOGI(MAIN_TAG, "BLE GATT initialized (scene + brightness)");
}

/* ── Splash font (ASCII 32-90) ────────────────────────────── */

static const uint8_t font5x7[][5] = {
    {0x00,0x00,0x00,0x00,0x00}, {0x00,0x00,0x5F,0x00,0x00},
    {0x00,0x07,0x00,0x07,0x00}, {0x14,0x7F,0x14,0x7F,0x14},
    {0x24,0x2A,0x7F,0x2A,0x12}, {0x23,0x13,0x08,0x64,0x62},
    {0x36,0x49,0x55,0x22,0x50}, {0x00,0x00,0x07,0x00,0x00},
    {0x00,0x1C,0x22,0x41,0x00}, {0x00,0x41,0x22,0x1C,0x00},
    {0x14,0x08,0x3E,0x08,0x14}, {0x08,0x08,0x3E,0x08,0x08},
    {0x00,0x50,0x30,0x00,0x00}, {0x08,0x08,0x08,0x08,0x08},
    {0x00,0x60,0x60,0x00,0x00}, {0x20,0x10,0x08,0x04,0x02},
    {0x3E,0x51,0x49,0x45,0x3E}, {0x00,0x42,0x7F,0x40,0x00},
    {0x42,0x61,0x51,0x49,0x46}, {0x21,0x41,0x45,0x4B,0x31},
    {0x18,0x14,0x12,0x7F,0x10}, {0x27,0x45,0x45,0x45,0x39},
    {0x3C,0x4A,0x49,0x49,0x30}, {0x01,0x71,0x09,0x05,0x03},
    {0x36,0x49,0x49,0x49,0x36}, {0x06,0x49,0x49,0x29,0x1E},
    {0x00,0x36,0x36,0x00,0x00}, {0x00,0x56,0x36,0x00,0x00},
    {0x08,0x14,0x22,0x41,0x00}, {0x14,0x14,0x14,0x14,0x14},
    {0x00,0x41,0x22,0x14,0x08}, {0x02,0x01,0x51,0x09,0x06},
    {0x3E,0x41,0x5D,0x55,0x5E}, {0x7E,0x09,0x09,0x09,0x7E},
    {0x7F,0x49,0x49,0x49,0x36}, {0x3E,0x41,0x41,0x41,0x22},
    {0x7F,0x41,0x41,0x22,0x1C}, {0x7F,0x49,0x49,0x49,0x41},
    {0x7F,0x09,0x09,0x09,0x01}, {0x3E,0x41,0x49,0x49,0x7A},
    {0x7F,0x08,0x08,0x08,0x7F}, {0x00,0x41,0x7F,0x41,0x00},
    {0x20,0x40,0x41,0x3F,0x01}, {0x7F,0x08,0x14,0x22,0x41},
    {0x7F,0x40,0x40,0x40,0x40}, {0x7F,0x02,0x0C,0x02,0x7F},
    {0x7F,0x04,0x08,0x10,0x7F}, {0x3E,0x41,0x41,0x41,0x3E},
    {0x7F,0x09,0x09,0x09,0x06}, {0x3E,0x41,0x51,0x21,0x5E},
    {0x7F,0x09,0x19,0x29,0x46}, {0x46,0x49,0x49,0x49,0x31},
    {0x01,0x01,0x7F,0x01,0x01}, {0x3F,0x40,0x40,0x40,0x3F},
    {0x1F,0x20,0x40,0x20,0x1F}, {0x3F,0x40,0x38,0x40,0x3F},
    {0x63,0x14,0x08,0x14,0x63}, {0x07,0x08,0x70,0x08,0x07},
    {0x61,0x51,0x49,0x45,0x43},
};

static void draw_char(uint16_t *row_buf, int rx, int ry, char ch, int y, uint16_t color) {
    if (ch < 32 || ch > 90) ch = '?';
    int idx = ch - 32;
    int fy = y - ry;
    if (fy < 0 || fy >= 14) return;
    int bit = fy / 2;
    for (int cx = 0; cx < 5; cx++) {
        if (font5x7[idx][cx] & (1 << bit)) {
            int px = rx + cx * 2;
            if (px >= 0 && px + 1 < LCD_H_RES) {
                row_buf[px] = color;
                row_buf[px + 1] = color;
            }
        }
    }
}

static void draw_string(uint16_t *row_buf, int x, int ry, const char *str, int y, uint16_t color) {
    for (int i = 0; str[i]; i++)
        draw_char(row_buf, x + i * 14, ry, str[i], y, color);
}

/* draw_frame() is defined in draw_frame.c — the only file recompiled on-device */
extern void draw_frame(void);

/* ── UART command task (brightness + SDL scene) ───────────── */
/* Scans UART0 for:
 *   0xC0 0x5D 0x42 <percent>           → brightness
 *   0xC0 0x5D 0x4C <len_lo> <len_hi> <data...> → SDL scene
 * Writes SDL scenes to ble_scene_buf so draw_frame() can render them. */
#include "driver/uart.h"
static void uart_cmd_task(void *arg) {
    uart_config_t cfg = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
    };
    uart_param_config(UART_NUM_0, &cfg);
    uart_driver_install(UART_NUM_0, BLE_SCENE_BUF_SIZE * 2, 0, 0, NULL, 0);

    uint8_t buf[128];
    // States: 0=wait 0xC0, 1=wait 0x5D, 2=wait cmd byte
    //   brightness: 3=wait percent
    //   SDL scene: 10=wait len_lo, 11=wait len_hi, 12=reading scene data
    int state = 0;
    int scene_len = 0, scene_off = 0;
    uint8_t scene_buf[BLE_SCENE_BUF_SIZE];

    while (1) {
        int len = uart_read_bytes(UART_NUM_0, buf, sizeof(buf), 50 / portTICK_PERIOD_MS);
        for (int i = 0; i < len; i++) {
            switch (state) {
            case 0: if (buf[i] == 0xC0) state = 1; break;
            case 1: state = (buf[i] == 0x5D) ? 2 : (buf[i] == 0xC0 ? 1 : 0); break;
            case 2:
                if (buf[i] == 0x42) state = 3;        // brightness
                else if (buf[i] == 0x4C) state = 10;  // SDL scene
                else state = (buf[i] == 0xC0) ? 1 : 0;
                break;
            case 3: {  // brightness percent
                int pct = buf[i] > 100 ? 100 : buf[i];
                display_set_brightness(pct);
                ESP_LOGI(MAIN_TAG, "UART brightness: %d%%", pct);
                state = 0;
                break;
            }
            case 10:  // SDL len low byte
                scene_buf[0] = buf[i];
                state = 11;
                break;
            case 11: {  // SDL len high byte
                scene_len = scene_buf[0] | (buf[i] << 8);
                if (scene_len > 0 && scene_len <= BLE_SCENE_BUF_SIZE) {
                    scene_off = 0;
                    // Consume remaining bytes in this buffer
                    int avail = len - (i + 1);
                    int take = avail < scene_len ? avail : scene_len;
                    if (take > 0) {
                        memcpy(scene_buf, &buf[i + 1], take);
                        scene_off = take;
                        i += take;
                    }
                    if (scene_off >= scene_len) {
                        // Complete — copy to shared buffer
                        memcpy((void *)ble_scene_buf, scene_buf, scene_len);
                        ble_scene_len = scene_len;
                        ble_scene_ready = 1;
                        ESP_LOGI(MAIN_TAG, "UART SDL scene: %d bytes", scene_len);
                        state = 0;
                    } else {
                        state = 12;  // need more data
                    }
                } else {
                    state = 0;
                }
                break;
            }
            case 12: {  // reading scene data
                scene_buf[scene_off++] = buf[i];
                if (scene_off >= scene_len) {
                    memcpy((void *)ble_scene_buf, scene_buf, scene_len);
                    ble_scene_len = scene_len;
                    ble_scene_ready = 1;
                    ESP_LOGI(MAIN_TAG, "UART SDL scene: %d bytes", scene_len);
                    state = 0;
                }
                break;
            }
            }
        }
    }
}

void app_main(void) {
    display_init();
    backlight_init();
    ble_init();

    // Start UART command listener (brightness + SDL scene) in background
    xTaskCreate(uart_cmd_task, "uart_cmd", 8192, NULL, 5, NULL);

    draw_frame();

    while (1) { vTaskDelay(pdMS_TO_TICKS(10000)); }
}
