#include <gtest/gtest.h>
#include "Network/NetworkService.h"
#include "mockware/fakes.h"

TEST(network, init_registers_event_handlers) {
    nvs_flash_init_mock = +[]() -> esp_err_t { return ESP_OK; };
    nvs_open_mock = +[](const char*, nvs_open_mode_t, nvs_handle_t* out) -> esp_err_t {
        *out = (nvs_handle_t)0xABCD;
        return ESP_OK;
    };
    nvs_get_str_mock = +[](nvs_handle_t, const char*, char* out_value, size_t* out_length) -> esp_err_t {
        if (out_value == nullptr && out_length != nullptr) {
            *out_length = 1;
            return ESP_ERR_NVS_NOT_FOUND;
        }
        return ESP_ERR_NVS_NOT_FOUND;
    };
    esp_event_handler_register_mock = +[](esp_event_base_t, int32_t, esp_event_handler_t, void*) -> esp_err_t {
        return ESP_OK;
    };
    xTaskCreate_mock = +[](TaskFunction_t, const char*, int, void*, int, TaskHandle_t*) -> int {
        return pdPASS;
    };

    bool result = NetworkService::init();
    EXPECT_TRUE(result);
    EXPECT_EQ(NetworkService::getOpenThreadTaskHandle(), nullptr);
}
