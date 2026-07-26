#pragma once

#include "nvs.h"
#include "nvs_flash.h"
#include "esp_err.h"

namespace NvsStorage
{
    constexpr auto STORAGE_NAMESPACE = "storage";

    inline nvs_handle_t s_handle = 0;
    inline bool s_initialized = false;

    inline esp_err_t open_if_needed()
    {
        if (s_initialized)
            return ESP_OK;

        const esp_err_t err = nvs_open(STORAGE_NAMESPACE,
                                 NVS_READWRITE,
                                 &s_handle);
        if (err == ESP_OK)
            s_initialized = true;

        return err;
    }

    inline bool init()
    {
        esp_err_t err = nvs_flash_init();

        if (err == ESP_ERR_NVS_NO_FREE_PAGES ||
            err == ESP_ERR_NVS_NEW_VERSION_FOUND)
        {
            ESP_ERROR_CHECK(nvs_flash_erase());
            err = nvs_flash_init();
        }

        if (err != ESP_OK)
            return false;

        err = open_if_needed();
        return err == ESP_OK;
    }

    template<typename T>
    bool save(const char* key, const T& data)
    {
        static_assert(std::is_trivially_copyable_v<T>,
              "save<T> only supports trivially copyable types");

        esp_err_t err = open_if_needed();
        if (err != ESP_OK)
            return false;

        err = nvs_set_blob(s_handle, key, &data, sizeof(T));
        if (err != ESP_OK)
            return false;

        err = nvs_commit(s_handle);
        return err == ESP_OK;
    }

    inline bool save(const char* key, const std::string& value)
    {
        esp_err_t err = open_if_needed();
        if (err != ESP_OK)
            return false;

        err = nvs_set_str(s_handle, key, value.c_str());
        if (err != ESP_OK)
            return false;

        return nvs_commit(s_handle) == ESP_OK;
    }

    template<typename T>
    bool load(const char* key, T& data)
    {
        esp_err_t err = open_if_needed();
        if (err != ESP_OK)
            return false;

        size_t required_size = sizeof(T);

        err = nvs_get_blob(s_handle,
                           key,
                           &data,
                           &required_size);

        if (err == ESP_ERR_NVS_NOT_FOUND)
            return false;

        if (required_size != sizeof(T))
            return false;//ESP_ERR_INVALID_SIZE;

        return true;
    }

    inline bool load(const char* key, std::string& value)
    {
        esp_err_t err = open_if_needed();
        if (err != ESP_OK)
            return false;

        size_t requiredSize = 0;

        err = nvs_get_str(s_handle, key, nullptr, &requiredSize);
        if (err != ESP_OK)
            return false;

        std::string buffer;
        buffer.resize(requiredSize);  // includes null terminator

        err = nvs_get_str(s_handle, key, buffer.data(), &requiredSize);
        if (err != ESP_OK)
            return false;

        // remove trailing null
        if (!buffer.empty() && buffer.back() == '\0') {
            buffer.pop_back();
        }

        value = std::move(buffer);
        return true;
    }

    inline bool erase(const char* key)
    {
        esp_err_t err = open_if_needed();
        if (err != ESP_OK)
            return false;

        err = nvs_erase_key(s_handle, key);
        if (err != ESP_OK)
            return false;

        err =  nvs_commit(s_handle);
        return err == ESP_OK;
    }

}