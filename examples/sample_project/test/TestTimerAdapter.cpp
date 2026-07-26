#include <gtest/gtest.h>
#include "TimerAdapter.h"
#include "mockware/fakes.h"

static bool timer_create_called = false;
static bool timer_start_called = false;
static bool timer_stop_called = false;

TEST(timer, startOnce_calls_esp_timer_create_and_start_once) {
    timer_create_called = false;
    timer_start_called = false;

    esp_timer_create_mock = +[](const esp_timer_create_args_t* args,
                                 esp_timer_handle_t* out_handle) -> esp_err_t {
        timer_create_called = true;
        EXPECT_NE(args, nullptr);
        EXPECT_NE(args->callback, nullptr);
        EXPECT_NE(out_handle, nullptr);
        *out_handle = (esp_timer_handle_t)0x1234;
        return ESP_OK;
    };

    esp_timer_start_once_mock = +[](esp_timer_handle_t timer,
                                     uint64_t timeout_us) -> esp_err_t {
        timer_start_called = true;
        EXPECT_EQ(timer, (esp_timer_handle_t)0x1234);
        EXPECT_GT(timeout_us, 0);
        return ESP_OK;
    };

    auto callback = []() { };
    TimerAdapter::startOnce("test_timer", 100, callback);

    EXPECT_TRUE(timer_create_called);
    EXPECT_TRUE(timer_start_called);
}

TEST(timer, stopAll_calls_esp_timer_stop) {
    timer_stop_called = false;

    esp_timer_stop_mock = +[](esp_timer_handle_t timer) -> esp_err_t {
        timer_stop_called = true;
        EXPECT_NE(timer, nullptr);
        return ESP_OK;
    };

    esp_timer_create_mock = +[](const esp_timer_create_args_t*,
                                 esp_timer_handle_t* out) -> esp_err_t {
        *out = (esp_timer_handle_t)0x5678;
        return ESP_OK;
    };

    esp_timer_start_once_mock = +[](esp_timer_handle_t, uint64_t) -> esp_err_t {
        return ESP_OK;
    };

    auto callback = []() { };
    TimerAdapter::startOnce("test_timer_2", 50, callback);
    TimerAdapter::stopAll();

    EXPECT_TRUE(timer_stop_called);
}
