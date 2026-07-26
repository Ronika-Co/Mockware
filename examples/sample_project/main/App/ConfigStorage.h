#pragma once

#include "Support.h"

namespace ConfigStorage {
    static constexpr auto TAG = "ConfigStorage";

    static constexpr auto defaultConnectionConfig = Connection::Config{
        .port = 5683,
        .server = "10.10.10.1",
        .token = "token",
        .ssid = "ssid",
        .password = "password",
        .useWifi = false,
    };

    bool init();

    bool saveConnectionConfig(const Connection::Config &config);

    bool eraseConnectionConfig();

    Connection::Config readConnectionConfig();

    bool changeOverhaulMode(bool mode);

    bool isInOverhaulMode();
}
