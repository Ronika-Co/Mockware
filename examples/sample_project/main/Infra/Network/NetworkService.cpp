#include "NetworkService.h"

#include "freertos/task.h"
#include "ConfigStorage.h"
#include "esp_log.h"
#include "OpenThreadService.h"
#include "TimeService.h"
#include "WifiService.h"

ESP_EVENT_DEFINE_BASE(NETWORK_EVENT);

namespace NetworkService
{
    static TaskHandle_t s_openThreadTaskHandle = nullptr;

    static void networkEventHandler(void *arg, esp_event_base_t event_base, int32_t event_id, void *event_data)
    {
        if (event_base != NETWORK_EVENT)
        {
            return;
        }

        if (event_id == NETWORK_EVENT_CONNECTED)
        {
            ESP_LOGD(TAG, "network is ready. inti time and edge service");
        }
    }

    static void coapEventHandler(void *arg, esp_event_base_t event_base, int32_t event_id, void *event_data)
    {
        if (event_base != COAP_EVENT)
        {
            return;
        }
        if (event_id == COAP_EVENT_CONNECTED)
        {
            ESP_LOGD(TAG, "network is ready. inti time and edge service");
        }
        else if (event_id == COAP_EVENT_DISCONNECTED)
        {
        }
    }

    static void batteryEventHandler(void *arg, esp_event_base_t event_base, int32_t event_id, void *event_data)
    {
        if (event_base != BATTERY_EVENT)
        {
            return;
        }
        const auto connConfig = ConfigStorage::readConnectionConfig();

        if (event_id == ON_POWER_EVENT)
        {
            if (connConfig.useWifi)
            {
                WifiService::start();
            }
            else
            {
                OpenThreadService::start();
            }
        }
        else if (event_id == ON_BATTERY_EVENT)
        {
            if (connConfig.useWifi)
            {
                WifiService::stop();
            }
            else
            {
                OpenThreadService::stop();
            }
        }
    }

    bool init()
    {
        esp_event_handler_register(NETWORK_EVENT, NETWORK_EVENT_CONNECTED, &networkEventHandler, nullptr);
        esp_event_handler_register(BATTERY_EVENT, ON_POWER_EVENT, &batteryEventHandler, nullptr);
        esp_event_handler_register(BATTERY_EVENT, ON_BATTERY_EVENT, &batteryEventHandler, nullptr);
        esp_event_handler_register(COAP_EVENT, COAP_EVENT_CONNECTED, &coapEventHandler, nullptr);

        const auto connConfig = ConfigStorage::readConnectionConfig();

        if (connConfig.useWifi)
        {
            ESP_LOGI(TAG, "Starting WiFi transport");
            WifiService::init(connConfig.ssid, connConfig.password);
        }
        else
        {
            ESP_LOGI(TAG, "Starting OpenThread transport");
            xTaskCreate(
                OpenThreadService::taskHandler,
                "open_thread_task_handler",
                8192,
                nullptr,
                5,
                &s_openThreadTaskHandle);
        }

        return true;
    }

    TaskHandle_t getOpenThreadTaskHandle() { return s_openThreadTaskHandle; }
}
