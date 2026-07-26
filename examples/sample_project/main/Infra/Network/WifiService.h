#pragma once

#include <cstdint>
#include <string>

namespace WifiService {
    static constexpr auto TAG = "WiFiService";

    void init(bool apMode, const std::string &ssid, const std::string &password);

    inline void init(const std::string &ssid, const std::string &password) {
        init(false, ssid, password);
    }

    void deinit();

    bool start();

    bool stop();

    bool isConnected();

    const char *getStatusString();

    void reconnect();

    const char *getIPAddress();

    int getRSSI();
}
