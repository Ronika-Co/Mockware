#include "Main.h"

#include "esp_err.h"
#include "esp_event.h"
#include "esp_vfs_eventfd.h"
#include "esp_ota_ops.h"

#include "Support.h"
#include "NvsStorage.h"
#include "WifiService.h"
#include "Configs.h"
#include "ConfigStorage.h"
#include "esp_netif.h"
#include "OpenThreadService.h"
#include "TimeService.h"
#include "NetworkService.h"
#include "esp_heap_caps.h"

static constexpr auto TAG = "Main";

std::string device_version;

#ifdef __cplusplus
extern "C"
{
#endif

    void print_system_info()
    {
        const esp_app_desc_t *app_desc = esp_app_get_description();
        device_version = std::string("v") + app_desc->version;

        ESP_LOGI(TAG, "==========================================");
        ESP_LOGI(TAG, "============== Dahir Device ==============");
        ESP_LOGI(TAG, "==========================================");
        ESP_LOGI(TAG, "Project Name:    %s", app_desc->project_name);
        ESP_LOGI(TAG, "Firmware Version: %s", app_desc->version);
        ESP_LOGI(TAG, "Compile Time:    %s %s", app_desc->date, app_desc->time);
        ESP_LOGI(TAG, "==========================================");
        ESP_LOGI(TAG, "==========================================");
    }

    void system_setup()
    {
        NvsStorage::init();

        constexpr esp_vfs_eventfd_config_t eventfd_config = {
            .max_fds = 4,
        };
        ESP_ERROR_CHECK(esp_event_loop_create_default());
        ESP_ERROR_CHECK(esp_netif_init());
        ESP_ERROR_CHECK(esp_vfs_eventfd_register(&eventfd_config));
        ESP_ERROR_CHECK(LittleFS::init());

        esp_log_level_set("*", ESP_LOG_INFO);
        esp_log_level_set(Connection::Config::TAG, ESP_LOG_DEBUG);
        esp_log_level_set(OpenThreadService::TAG, ESP_LOG_DEBUG);
    }

    void hardware_setup()
    {
        ConfigStorage::init();
        TimeService::init();
    }

    void app_main()
    {
        print_system_info();
        system_setup();
        hardware_setup();

        NetworkService::init();
    }

#ifdef __cplusplus
}
#endif
