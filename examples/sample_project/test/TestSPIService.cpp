#include <gtest/gtest.h>
#include "SPI/SPIService.h"
#include "mockware/fakes.h"

TEST(spi, init_calls_spi_bus_initialize) {
    spi_bus_initialize_mock = +[](spi_host_device_t, const spi_bus_config_t*, int) -> esp_err_t {
        return ESP_OK;
    };

    bool result = SPIService::init();
    EXPECT_TRUE(result);
}

TEST(spi, init_returns_false_on_failure) {
    spi_bus_initialize_mock = +[](spi_host_device_t, const spi_bus_config_t*, int) -> esp_err_t {
        return ESP_FAIL;
    };

    bool result = SPIService::init();
    EXPECT_FALSE(result);
}
