#include "TimeService.h"
#include <ctime>
#include <sys/time.h>

#include "ConfigStorage.h"
#include "esp_sntp.h"

#include "Support.h"

namespace TimeService
{
    static constexpr auto TAG = "TimeService";
    static constexpr auto TIME_ZONE_KEY = "TZ";
    static constexpr auto TIME_ZONE_CODE = "IRST-3:30";
    static std::string dahirServerIp;

    bool isInitialized = false;

    void timeSyncNotificationCallback(struct timeval *tv)
    {
        ESP_LOGD(TAG, "NTP sync done, updating RTC");

        time_t now;
        time(&now);

        tm utcTime{};
        gmtime_r(&now, &utcTime);

        auto [hour, minute, second] = getLocalTime();
        ESP_LOGD(TAG, "Local time is: %02u:%02u:%02u", hour, minute, second);
    }

    bool init()
    {
        if (isInitialized)
        {
            ESP_LOGD(TAG, "already initialized");
            return true;
        }

        setenv(TIME_ZONE_KEY, TIME_ZONE_CODE, 1);
        tzset();

        esp_sntp_setoperatingmode(ESP_SNTP_OPMODE_POLL);
        esp_sntp_setservername(0, "0.asia.pool.ntp.org");
        esp_sntp_set_sync_mode(SNTP_SYNC_MODE_IMMED);

        sntp_set_time_sync_notification_cb(timeSyncNotificationCallback);

        sntp_set_sync_interval(15 * 60 * 1000);

        esp_sntp_init();

        isInitialized = true;
        ESP_LOGD(TAG, "initialized");
        auto [hour, minute, second] = getLocalTime();
        ESP_LOGI(TAG, "Local time is: %02u:%02u:%02u", hour, minute, second);

        return true;
    }

    void forceSync()
    {
        if (isInitialized)
        {
            ESP_LOGI(TAG, "Forcing time synchronization");
            sntp_restart();
        }
        else
        {
            ESP_LOGW(TAG, "TimeService not initialized, cannot force sync");
        }
    }

    uint64_t getCurrentTimeStamp()
    {
        timeval tv{};
        gettimeofday(&tv, nullptr);
        // Convert seconds + microseconds to milliseconds
        return static_cast<uint64_t>(tv.tv_sec) * 1000 + tv.tv_usec / 1000;
    }

    uint16_t getMinutesPassedFromDay()
    {
        time_t now;
        tm local_time{};

        time(&now);
        localtime_r(&now, &local_time);

        // Calculate minutes from midnight
        return static_cast<uint16_t>(local_time.tm_hour * 60 + local_time.tm_min);
    }

    LocalTime getLocalTime()
    {
        time_t now;
        LocalTime current_time{};
        tm local_time{};

        time(&now);
        localtime_r(&now, &local_time);
        current_time.hour = local_time.tm_hour;
        current_time.minute = local_time.tm_min;
        current_time.second = local_time.tm_sec;
        return current_time;
    }
}
