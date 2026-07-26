#include "Support.h"

#include "cJSON.h"
#include "esp_timer.h"

namespace Utils {
    uint64_t millis() {
        return esp_timer_get_time() / 1000;
    }
}

namespace Connection {
    static constexpr auto PORT_KEY = "port";
    static constexpr auto SERVER_KEY = "server";
    static constexpr auto TOKEN_KEY = "token";
    static constexpr auto SSID_KEY = "ssid";
    static constexpr auto PASS_KEY = "password";
    static constexpr auto USE_WIFI_KEY = "useWifi";

    std::string Config::toJsonString() const {
        cJSON *root = cJSON_CreateObject();

        cJSON_AddNumberToObject(root, PORT_KEY, port);
        cJSON_AddStringToObject(root, SSID_KEY, ssid.c_str());
        cJSON_AddStringToObject(root, PASS_KEY, password.c_str());
        cJSON_AddStringToObject(root, SERVER_KEY, server.c_str());
        cJSON_AddStringToObject(root, TOKEN_KEY, token.c_str());
        cJSON_AddBoolToObject(root, USE_WIFI_KEY, useWifi);

        char *json = cJSON_PrintUnformatted(root);

        std::string result;
        if (json) {
            result = json;
            free(json);
        }

        cJSON_Delete(root);
        return result;
    }

    Config Config::parse(const std::string &jsonStr, const Config &defaultConfig) {
        Config config = defaultConfig;

        if (jsonStr.empty()) {
            return config;
        }

        cJSON *root = cJSON_Parse(jsonStr.c_str());
        if (!root) {
            return config;
        }

        const cJSON *item = nullptr;

        item = cJSON_GetObjectItem(root, PORT_KEY);
        if (cJSON_IsNumber(item)) {
            config.port = static_cast<uint16_t>(item->valueint);
        }

        item = cJSON_GetObjectItem(root, SSID_KEY);
        if (cJSON_IsString(item) && item->valuestring) {
            config.ssid = item->valuestring;
        }

        item = cJSON_GetObjectItem(root, PASS_KEY);
        if (cJSON_IsString(item) && item->valuestring) {
            config.password = item->valuestring;
        }

        item = cJSON_GetObjectItem(root, SERVER_KEY);
        if (cJSON_IsString(item) && item->valuestring) {
            config.server = item->valuestring;
        }

        item = cJSON_GetObjectItem(root, TOKEN_KEY);
        if (cJSON_IsString(item) && item->valuestring) {
            config.token = item->valuestring;
        }

        item = cJSON_GetObjectItem(root, USE_WIFI_KEY);
        if (cJSON_IsBool(item)) {
            config.useWifi = cJSON_IsTrue(item);
        }

        cJSON_Delete(root);
        return config;
    }
}
