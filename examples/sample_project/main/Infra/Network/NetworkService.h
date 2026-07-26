#pragma once

#include "esp_event.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

ESP_EVENT_DECLARE_BASE(NETWORK_EVENT);

typedef enum {
    NETWORK_EVENT_CONNECTED,
    NETWORK_EVENT_DISCONNECTED,
} network_event_id_t;

namespace NetworkService {
    static constexpr auto TAG = "NetworkService";

    bool init();

    TaskHandle_t getOpenThreadTaskHandle();
}
