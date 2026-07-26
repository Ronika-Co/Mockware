#pragma once
#include "hal/spi_types.h"

namespace SPIService {
    static constexpr auto TAG = "SPIService";

    constexpr spi_host_device_t SPI_HOST = SPI2_HOST;

    bool init();
}
