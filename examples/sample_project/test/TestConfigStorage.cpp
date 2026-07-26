#include <gtest/gtest.h>
#include <cstring>
#include "ConfigStorage.h"
#include "mockware/fakes.h"

static bool nvs_save_called = false;
static bool nvs_load_called = false;
static bool nvs_erase_called = false;

static void reset_flags() {
    nvs_save_called = false;
    nvs_load_called = false;
    nvs_erase_called = false;
}

TEST(config, init_loads_connection_config_from_NVS) {
    reset_flags();
    nvs_flash_init_mock = +[]() -> esp_err_t { return ESP_OK; };
    nvs_open_mock = +[](const char*, nvs_open_mode_t, nvs_handle_t* out) -> esp_err_t {
        *out = (nvs_handle_t)0xABCD;
        return ESP_OK;
    };
    nvs_get_str_mock = +[](nvs_handle_t, const char*, char* out_value, size_t* out_length) -> esp_err_t {
        nvs_load_called = true;
        if (out_value == nullptr && out_length != nullptr) {
            *out_length = 20;
            return ESP_OK;
        }
        if (out_value != nullptr) {
            const char* json = "{\"port\":5683}";
            std::strcpy(out_value, json);
            *out_length = std::strlen(json) + 1;
        }
        return ESP_OK;
    };

    bool result = ConfigStorage::init();
    EXPECT_TRUE(result);
    EXPECT_TRUE(nvs_load_called);
    auto config = ConfigStorage::readConnectionConfig();
    EXPECT_EQ(config.port, 5683);
}

TEST(config, saveConnectionConfig_calls_NvsStorage_save) {
    reset_flags();
    nvs_flash_init_mock = +[]() -> esp_err_t { return ESP_OK; };
    nvs_open_mock = +[](const char*, nvs_open_mode_t, nvs_handle_t* out) -> esp_err_t {
        *out = (nvs_handle_t)0xABCD;
        return ESP_OK;
    };
    nvs_set_str_mock = +[](nvs_handle_t, const char*, const char*) -> esp_err_t {
        nvs_save_called = true;
        return ESP_OK;
    };
    nvs_commit_mock = +[](nvs_handle_t) -> esp_err_t { return ESP_OK; };

    ConfigStorage::init();
    Connection::Config testConfig{};
    bool result = ConfigStorage::saveConnectionConfig(testConfig);
    EXPECT_TRUE(result);
    EXPECT_TRUE(nvs_save_called);
}

TEST(config, eraseConnectionConfig_calls_NvsStorage_erase) {
    reset_flags();
    nvs_flash_init_mock = +[]() -> esp_err_t { return ESP_OK; };
    nvs_open_mock = +[](const char*, nvs_open_mode_t, nvs_handle_t* out) -> esp_err_t {
        *out = (nvs_handle_t)0xABCD;
        return ESP_OK;
    };
    nvs_erase_key_mock = +[](nvs_handle_t, const char*) -> esp_err_t {
        nvs_erase_called = true;
        return ESP_OK;
    };
    nvs_commit_mock = +[](nvs_handle_t) -> esp_err_t { return ESP_OK; };

    ConfigStorage::init();
    bool result = ConfigStorage::eraseConnectionConfig();
    EXPECT_TRUE(result);
    EXPECT_TRUE(nvs_erase_called);
}

TEST(config, overhaul_mode_round_trips) {
    reset_flags();
    nvs_flash_init_mock = +[]() -> esp_err_t { return ESP_OK; };
    nvs_open_mock = +[](const char*, nvs_open_mode_t, nvs_handle_t* out) -> esp_err_t {
        *out = (nvs_handle_t)0xABCD;
        return ESP_OK;
    };
    nvs_set_blob_mock = +[](nvs_handle_t, const char*, const void*, size_t) -> esp_err_t {
        nvs_save_called = true;
        return ESP_OK;
    };
    nvs_commit_mock = +[](nvs_handle_t) -> esp_err_t { return ESP_OK; };
    nvs_get_blob_mock = +[](nvs_handle_t, const char*, void*, size_t*) -> esp_err_t {
        return ESP_ERR_NVS_NOT_FOUND;
    };

    ConfigStorage::init();
    EXPECT_FALSE(ConfigStorage::isInOverhaulMode());
    bool result = ConfigStorage::changeOverhaulMode(true);
    EXPECT_TRUE(result);
    EXPECT_TRUE(nvs_save_called);
    EXPECT_TRUE(ConfigStorage::isInOverhaulMode());
}
