#include "wifi_manager.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "esp_err.h"

wifi_mgr_status_t wifi_manager_start(void) {
    esp_err_t ret;

    ret = nvs_flash_init();
    if (ret != ESP_OK) {
        return WIFI_MGR_FAIL;
    }

    ret = esp_wifi_start();
    if (ret != ESP_OK) {
        return WIFI_MGR_FAIL;
    }

    return WIFI_MGR_OK;
}

wifi_mgr_status_t wifi_manager_stop(void) {
    esp_err_t ret = esp_wifi_stop();
    return (ret == ESP_OK) ? WIFI_MGR_OK : WIFI_MGR_FAIL;
}
