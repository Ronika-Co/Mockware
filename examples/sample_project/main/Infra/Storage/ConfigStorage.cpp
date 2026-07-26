#include "ConfigStorage.h"
#include "NvsStorage.h"

namespace ConfigStorage {
    constexpr auto CONNECTION_KEY = "conn_cfg";
    constexpr auto OVERHAUL_KEY = "ovr";

    static Connection::Config latestConnectionConfig = defaultConnectionConfig;
    static bool overhaulMode = false;

    bool init() {
        std::string config;
        if (NvsStorage::load(CONNECTION_KEY, config)) {
            latestConnectionConfig = Connection::Config::parse(config, defaultConnectionConfig);
        }

        NvsStorage::load(OVERHAUL_KEY, overhaulMode);
        return true;
    }

    bool saveConnectionConfig(const Connection::Config &config) {
        if (config == latestConnectionConfig) {
            return true;
        }
        const auto jsonConfig = config.toJsonString();
        if (!NvsStorage::save(CONNECTION_KEY, jsonConfig)) {
            return false;
        }
        latestConnectionConfig = config;
        return true;
    }

    bool eraseConnectionConfig() {
        latestConnectionConfig = defaultConnectionConfig;
        return NvsStorage::erase(CONNECTION_KEY);
    }

    Connection::Config readConnectionConfig() {
        return latestConnectionConfig;
    }

    bool changeOverhaulMode(const bool mode) {
        if (mode == overhaulMode) {
            return true;
        }

        if (!NvsStorage::save(OVERHAUL_KEY, mode)) {
            return false;
        }

        overhaulMode = mode;
        return true;
    }

    bool isInOverhaulMode() {
        return overhaulMode;
    }
}
