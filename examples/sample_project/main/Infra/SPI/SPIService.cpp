#include "SPIService.h"

#include "esp_log.h"
#include "driver/spi_common.h"
#include "freertos/FreeRTOS.h"
#include "soc/gpio_num.h"

namespace SPIService {

    constexpr gpio_num_t MOSI_GPIO = GPIO_NUM_12;
    constexpr gpio_num_t MISO_GPIO = GPIO_NUM_13;
    constexpr gpio_num_t SCLK_GPIO = GPIO_NUM_10;

    // static constexpr gpio_num_t MOSI_GPIO = GPIO_NUM_18;
    // static constexpr gpio_num_t SCLK_GPIO = GPIO_NUM_19;
    // static constexpr gpio_num_t MISO_GPIO = GPIO_NUM_20;

    bool init() {
        ESP_LOGD(TAG, "Initialize SPI bus");
        spi_bus_config_t bus_config{};
        bus_config.sclk_io_num = SCLK_GPIO;
        bus_config.mosi_io_num = MOSI_GPIO;
        bus_config.miso_io_num = MISO_GPIO;
        bus_config.quadwp_io_num = -1;
        bus_config.quadhd_io_num = -1;
        bus_config.max_transfer_sz = 100 * 50 * sizeof(uint16_t);

        const auto ret = spi_bus_initialize(SPI_HOST, &bus_config, SPI_DMA_CH_AUTO);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "fail to initialize spi bus");
            return false;
        }

        ESP_LOGD(TAG, "initialized");
        return true;
    }
}
