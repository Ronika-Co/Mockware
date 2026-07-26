#include <gtest/gtest.h>
#include "App/Support.h"
#include "mockware/fakes.h"

static int64_t mock_time_value = 0;

TEST(utils, millis_returns_mocked_time) {
    mock_time_value = 5000;
    esp_timer_get_time_mock = +[]() -> int64_t { return mock_time_value; };

    uint64_t result = Utils::millis();
    EXPECT_EQ(result, 5);
}

TEST(utils, millis_can_simulate_different_times) {
    mock_time_value = 0;
    esp_timer_get_time_mock = +[]() -> int64_t {
        static int64_t t = 0;
        t += 1000;
        return t;
    };

    EXPECT_EQ(Utils::millis(), 1);
    EXPECT_EQ(Utils::millis(), 2);
    EXPECT_EQ(Utils::millis(), 3);
}
