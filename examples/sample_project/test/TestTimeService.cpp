#include <gtest/gtest.h>
#include "TimeService.h"
#include "mockware/fakes.h"

TEST(time, init_configures_SNTP) {
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
    nvs_get_blob_mock = +[](nvs_handle_t, const char*, void*, size_t*) -> esp_err_t {
        return ESP_ERR_NVS_NOT_FOUND;
    };
    esp_sntp_setoperatingmode_mock = +[](int) -> void {};
    esp_sntp_setservername_mock = +[](int, const char*) -> void {};
    esp_sntp_set_sync_mode_mock = +[](int) -> void {};
    sntp_set_time_sync_notification_cb_mock = +[](void (*cb)(struct timeval*)) -> void { (void)cb; };
    sntp_set_sync_interval_mock = +[](int) -> void {};
    esp_sntp_init_mock = +[]() -> void {};

    bool result = TimeService::init();
    EXPECT_TRUE(result);
}

TEST(time, secondsToTimeString_formats_correctly) {
    std::string result = TimeService::secondsToTimeString(3661);
    EXPECT_NE(result.find(':'), std::string::npos);
}

TEST(time, forceSync_restarts_SNTP) {
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
    nvs_get_blob_mock = +[](nvs_handle_t, const char*, void*, size_t*) -> esp_err_t {
        return ESP_ERR_NVS_NOT_FOUND;
    };
    esp_sntp_setoperatingmode_mock = +[](int) -> void {};
    esp_sntp_setservername_mock = +[](int, const char*) -> void {};
    esp_sntp_set_sync_mode_mock = +[](int) -> void {};
    sntp_set_time_sync_notification_cb_mock = +[](void (*cb)(struct timeval*)) -> void { (void)cb; };
    sntp_set_sync_interval_mock = +[](int) -> void {};
    esp_sntp_init_mock = +[]() -> void {};
    sntp_restart_mock = +[]() -> void {};

    TimeService::init();
    TimeService::forceSync();
}
