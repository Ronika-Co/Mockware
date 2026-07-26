#pragma once
#include <cstdint>
#include <cstdio>
#include <string>

namespace TimeService {
    struct LocalTime {
        uint8_t hour; // 0-23
        uint8_t minute; // 0-59
        uint8_t second;
    };

    bool init();

    void forceSync();

    uint64_t getCurrentTimeStamp();

    uint16_t getMinutesPassedFromDay();

    LocalTime getLocalTime();

    inline std::string secondsToTimeString(const uint64_t seconds) {
        const uint64_t mins = seconds / 60;
        const uint64_t sec = seconds % 60;
        char buffer[32];
        snprintf(buffer, sizeof(buffer), "%02llu:%02llu", mins, sec);

        return std::string(buffer);
    };
}
