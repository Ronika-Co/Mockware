#include <gtest/gtest.h>
#include <cstring>
#include "Network/WifiService.h"
#include "mockware/fakes.h"

static bool wifi_init_called = false;
static bool wifi_start_called = false;
static bool wifi_stop_called = false;

static void reset_flags() {
    wifi_init_called = false;
    wifi_start_called = false;
    wifi_stop_called = false;
}

TEST(wifi, init_in_STA_mode_configures_WiFi) {
    reset_flags();
    nvs_flash_init_mock = +[]() -> esp_err_t { return ESP_OK; };
    nvs_open_mock = +[](const char*, nvs_open_mode_t, nvs_handle_t* out) -> esp_err_t {
        *out = (nvs_handle_t)0xABCD;
        return ESP_OK;
    };
    esp_netif_create_default_wifi_sta_mock = +[]() -> esp_netif_t* { return (esp_netif_t*)0x1; };
    esp_wifi_init_mock = +[](const wifi_init_config_t*) -> esp_err_t {
        wifi_init_called = true;
        return ESP_OK;
    };
    esp_wifi_set_mode_mock = +[](wifi_mode_t) -> esp_err_t { return ESP_OK; };
    esp_wifi_set_config_mock = +[](int, void*) -> esp_err_t { return ESP_OK; };
    esp_wifi_start_mock = +[]() -> esp_err_t {
        wifi_start_called = true;
        return ESP_OK;
    };
    esp_event_handler_register_mock = +[](esp_event_base_t, int32_t, esp_event_handler_t, void*) -> esp_err_t {
        return ESP_OK;
    };
    xEventGroupCreate_mock = +[]() -> EventGroupHandle_t { return (EventGroupHandle_t)0x1; };

    WifiService::init("test_ssid", "test_pass");

    EXPECT_TRUE(wifi_init_called);
    EXPECT_TRUE(wifi_start_called);
}

TEST(wifi, start_and_stop_work) {
    reset_flags();
    nvs_flash_init_mock = +[]() -> esp_err_t { return ESP_OK; };
    nvs_open_mock = +[](const char*, nvs_open_mode_t, nvs_handle_t* out) -> esp_err_t {
        *out = (nvs_handle_t)0xABCD;
        return ESP_OK;
    };
    esp_netif_create_default_wifi_sta_mock = +[]() -> esp_netif_t* { return (esp_netif_t*)0x1; };
    esp_wifi_init_mock = +[](const wifi_init_config_t*) -> esp_err_t {
        wifi_init_called = true;
        return ESP_OK;
    };
    esp_wifi_set_mode_mock = +[](wifi_mode_t) -> esp_err_t { return ESP_OK; };
    esp_wifi_set_config_mock = +[](int, void*) -> esp_err_t { return ESP_OK; };
    esp_wifi_start_mock = +[]() -> esp_err_t { return ESP_OK; };
    esp_wifi_stop_mock = +[]() -> esp_err_t {
        wifi_stop_called = true;
        return ESP_OK;
    };
    esp_event_handler_register_mock = +[](esp_event_base_t, int32_t, esp_event_handler_t, void*) -> esp_err_t {
        return ESP_OK;
    };
    xEventGroupCreate_mock = +[]() -> EventGroupHandle_t { return (EventGroupHandle_t)0x1; };

    WifiService::init("test_ssid", "test_pass");

    bool stopped = WifiService::stop();
    EXPECT_TRUE(stopped);
    EXPECT_TRUE(wifi_stop_called);
}

TEST(wifi, returns_correct_status_strings) {
    nvs_flash_init_mock = +[]() -> esp_err_t { return ESP_OK; };
    nvs_open_mock = +[](const char*, nvs_open_mode_t, nvs_handle_t* out) -> esp_err_t {
        *out = (nvs_handle_t)0xABCD;
        return ESP_OK;
    };
    esp_netif_create_default_wifi_sta_mock = +[]() -> esp_netif_t* { return (esp_netif_t*)0x1; };
    esp_wifi_init_mock = +[](const wifi_init_config_t*) -> esp_err_t { return ESP_OK; };
    esp_wifi_set_mode_mock = +[](wifi_mode_t) -> esp_err_t { return ESP_OK; };
    esp_wifi_set_config_mock = +[](int, void*) -> esp_err_t { return ESP_OK; };
    esp_wifi_start_mock = +[]() -> esp_err_t { return ESP_OK; };
    esp_event_handler_register_mock = +[](esp_event_base_t, int32_t, esp_event_handler_t, void*) -> esp_err_t {
        return ESP_OK;
    };
    xEventGroupCreate_mock = +[]() -> EventGroupHandle_t { return (EventGroupHandle_t)0x1; };

    WifiService::init("test_ssid", "test_pass");

    const char* status = WifiService::getStatusString();
    EXPECT_STREQ(status, "Disconnected");

    const char* ip = WifiService::getIPAddress();
    EXPECT_STREQ(ip, "0.0.0.0");

    int rssi = WifiService::getRSSI();
    EXPECT_EQ(rssi, 0);
}
