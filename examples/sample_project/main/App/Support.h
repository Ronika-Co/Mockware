#pragma once
#include <cstdint>
#include <string>

#include "esp_log.h"

#define SecToMillis(s) ((s) * 1000)
#define MillisToSec(s) ((s) / 1000)

namespace Utils
{
    uint64_t millis();
}

namespace Connection
{

    struct Config
    {
        static constexpr auto TAG = "Connection::Config";

        uint16_t port;
        std::string server;
        std::string token;
        std::string ssid;
        std::string password;
        bool useWifi = false;

        bool operator==(const Config &) const = default;

        void log() const
        {
            ESP_LOGD(TAG,
                     "port=%u, server=%s, token=%s, ssid=%s, password=%s, useWifi=%d",
                     port, server.data(), token.data(), ssid.data(), password.data(), useWifi);
        }

        std::string toJsonString() const;

        static Config parse(const std::string &jsonStr, const Config &defaultConfig);
    };
}
