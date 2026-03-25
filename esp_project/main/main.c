/* Placeholder — will be overwritten by the orchestrator on first run. */
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

void app_main(void)
{
    printf("ESP Vision Loop — waiting for generated code.\n");
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
