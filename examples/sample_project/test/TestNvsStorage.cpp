#include <gtest/gtest.h>
#include <cstring>
#include "Infra/Storage/NvsStorage.h"
#include "mockware/fakes.h"

static bool nvs_init_called = false;
static bool nvs_erase_called = false;
static bool nvs_set_called = false;
static bool nvs_commit_called = false;
static bool nvs_get_called = false;
static bool nvs_erase_key_called = false;
static int nvs_init_count = 0;

static void reset_flags() {
    nvs_init_called = false;
    nvs_erase_called = false;
    nvs_set_called = false;
    nvs_commit_called = false;
    nvs_get_called = false;
    nvs_erase_key_called = false;
    nvs_init_count = 0;
}

TEST(nvs, init_succeeds_on_first_try) {
    reset_flags();
    nvs_flash_init_mock = +[]() -> esp_err_t {
        nvs_init_called = true;
        return ESP_OK;
    };
    nvs_open_mock = +[](const char*, nvs_open_mode_t,
                         nvs_handle_t* out) -> esp_err_t {
        *out = (nvs_handle_t)0xABCD;
        return ESP_OK;
    };

    bool result = NvsStorage::init();
    EXPECT_TRUE(result);
    EXPECT_TRUE(nvs_init_called);
}

TEST(nvs, init_erases_and_retries_on_NO_FREE_PAGES) {
    reset_flags();
    nvs_init_count = 0;
    nvs_flash_init_mock = +[]() -> esp_err_t {
        nvs_init_count++;
        return (nvs_init_count == 1) ? ESP_ERR_NVS_NO_FREE_PAGES : ESP_OK;
    };
    nvs_flash_erase_mock = +[]() -> esp_err_t {
        nvs_erase_called = true;
        return ESP_OK;
    };
    nvs_open_mock = +[](const char*, nvs_open_mode_t,
                         nvs_handle_t* out) -> esp_err_t {
        *out = (nvs_handle_t)0xABCD;
        return ESP_OK;
    };

    bool result = NvsStorage::init();
    EXPECT_TRUE(result);
    EXPECT_TRUE(nvs_erase_called);
    EXPECT_EQ(nvs_init_count, 2);
}

TEST(nvs, save_string_calls_nvs_set_str_and_nvs_commit) {
    reset_flags();
    nvs_flash_init_mock = +[]() -> esp_err_t { return ESP_OK; };
    nvs_open_mock = +[](const char*, nvs_open_mode_t,
                         nvs_handle_t* out) -> esp_err_t {
        *out = (nvs_handle_t)0xABCD;
        return ESP_OK;
    };
    NvsStorage::init();

    nvs_set_str_mock = +[](nvs_handle_t handle, const char* key,
                            const char* value) -> esp_err_t {
        nvs_set_called = true;
        EXPECT_STREQ(key, "test_key");
        EXPECT_STREQ(value, "test_value");
        return ESP_OK;
    };
    nvs_commit_mock = +[](nvs_handle_t) -> esp_err_t {
        nvs_commit_called = true;
        return ESP_OK;
    };

    bool result = NvsStorage::save("test_key", std::string("test_value"));
    EXPECT_TRUE(result);
    EXPECT_TRUE(nvs_set_called);
    EXPECT_TRUE(nvs_commit_called);
}

TEST(nvs, load_string_calls_nvs_get_str) {
    reset_flags();
    nvs_flash_init_mock = +[]() -> esp_err_t { return ESP_OK; };
    nvs_open_mock = +[](const char*, nvs_open_mode_t,
                         nvs_handle_t* out) -> esp_err_t {
        *out = (nvs_handle_t)0xABCD;
        return ESP_OK;
    };
    NvsStorage::init();

    nvs_get_str_mock = +[](nvs_handle_t, const char*, char* out_value,
                            size_t* out_length) -> esp_err_t {
        nvs_get_called = true;
        if (out_value == nullptr && out_length != nullptr) {
            *out_length = 6;
            return ESP_OK;
        }
        if (out_value != nullptr && *out_length >= 6) {
            std::strcpy(out_value, "hello");
            *out_length = 6;
        }
        return ESP_OK;
    };

    std::string result;
    bool load_ok = NvsStorage::load("test_key", result);
    EXPECT_TRUE(load_ok);
    EXPECT_EQ(result, "hello");
    EXPECT_TRUE(nvs_get_called);
}

TEST(nvs, erase_calls_nvs_erase_key_and_nvs_commit) {
    reset_flags();
    nvs_flash_init_mock = +[]() -> esp_err_t { return ESP_OK; };
    nvs_open_mock = +[](const char*, nvs_open_mode_t,
                         nvs_handle_t* out) -> esp_err_t {
        *out = (nvs_handle_t)0xABCD;
        return ESP_OK;
    };
    NvsStorage::init();

    nvs_erase_key_mock = +[](nvs_handle_t, const char* key) -> esp_err_t {
        nvs_erase_key_called = true;
        EXPECT_STREQ(key, "test_key");
        return ESP_OK;
    };
    nvs_commit_mock = +[](nvs_handle_t) -> esp_err_t {
        nvs_commit_called = true;
        return ESP_OK;
    };

    bool result = NvsStorage::erase("test_key");
    EXPECT_TRUE(result);
    EXPECT_TRUE(nvs_erase_key_called);
    EXPECT_TRUE(nvs_commit_called);
}
