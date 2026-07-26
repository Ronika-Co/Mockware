#include <gtest/gtest.h>
#include "Network/OpenThreadService.h"
#include "mockware/fakes.h"

TEST(openthread, starts_and_stops) {
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

    bool started = OpenThreadService::start();
    EXPECT_TRUE(started);

    bool stopped = OpenThreadService::stop();
    EXPECT_TRUE(stopped);
}

TEST(openthread, tracks_disconnect_count) {
    uint32_t count = OpenThreadService::getDisconnectedCount();
    EXPECT_EQ(count, 0);
}
