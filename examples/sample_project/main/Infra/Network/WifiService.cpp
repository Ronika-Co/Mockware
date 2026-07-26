#include "WifiService.h"

#include <cstring>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"

#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_mac.h"
#include "esp_log.h"
#include "NetworkService.h"
#include "TimeService.h"

namespace WifiService
{

    static constexpr int WIFI_CONNECTED_BIT = BIT0;

    static constexpr uint8_t AP_CHANNEL = 1;
    static constexpr uint8_t AP_MAX_CONN = 4;

    static EventGroupHandle_t eventGroup = nullptr;

    static bool isInitialized = false;
    static bool isInAPMode = false;
    static bool wifiStarted = false;

    static char ipAddress[16] = "0.0.0.0";
    static esp_netif_t *staNetif = nullptr;
    static esp_netif_t *apNetif = nullptr;

    static int8_t rssi = 0;

    void updateIPAddress(const esp_ip4_addr_t ip)
    {
        snprintf(ipAddress, sizeof(ipAddress), IPSTR, IP2STR(&ip));
    }

    void eventHandler(void *arg, esp_event_base_t event_base, int32_t event_id, void *event_data)
    {

        if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START)
        {

            ESP_LOGI(TAG, "WiFi STA started, connecting...");
            esp_wifi_connect();
        }
        else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_STOP)
        {
            esp_event_post(NETWORK_EVENT, NETWORK_EVENT_DISCONNECTED, nullptr, 0, portMAX_DELAY);
        }
        else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED)
        {

            const auto *disconnected = static_cast<wifi_event_sta_disconnected_t *>(event_data);
            esp_event_post(NETWORK_EVENT, NETWORK_EVENT_DISCONNECTED, nullptr, 0, portMAX_DELAY);

            ESP_LOGW(TAG, "Disconnected, reason: %d - Retrying...", disconnected->reason);

            if (eventGroup)
            {
                xEventGroupClearBits(eventGroup, WIFI_CONNECTED_BIT);
            }

            strcpy(ipAddress, "0.0.0.0");
            rssi = 0;

            vTaskDelay(pdMS_TO_TICKS(1000));
            esp_wifi_connect();
        }

        else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP)
        {

            const auto event = static_cast<ip_event_got_ip_t *>(event_data);

            ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));

            updateIPAddress(event->ip_info.ip);

            wifi_ap_record_t apInfo;

            if (esp_wifi_sta_get_ap_info(&apInfo) == ESP_OK)
            {
                rssi = apInfo.rssi;
                ESP_LOGD(TAG, "RSSI: %d dBm", rssi);
            }

            if (eventGroup)
            {
                xEventGroupSetBits(eventGroup, WIFI_CONNECTED_BIT);
            }

            esp_event_post(NETWORK_EVENT, NETWORK_EVENT_CONNECTED, nullptr, 0, portMAX_DELAY);
        }
        else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_AP_START)
        {

            ESP_LOGI(TAG, "WiFi AP started");
        }

        else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_AP_STACONNECTED)
        {

            const auto *event = static_cast<wifi_event_ap_staconnected_t *>(event_data);

            ESP_LOGI(TAG, "Client connected: " MACSTR, MAC2STR(event->mac));
        }

        else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_AP_STADISCONNECTED)
        {

            const auto *event = static_cast<wifi_event_ap_stadisconnected_t *>(event_data);

            ESP_LOGI(TAG, "Client disconnected: " MACSTR, MAC2STR(event->mac));
        }
    }

    void init(bool apMode, const std::string &ssid, const std::string &password)
    {

        if (isInitialized)
        {
            ESP_LOGW(TAG, "already initialized");
            return;
        }

        isInAPMode = apMode;

        eventGroup = xEventGroupCreate();

        if (apMode)
        {
            apNetif = esp_netif_create_default_wifi_ap();
        }
        else
        {
            staNetif = esp_netif_create_default_wifi_sta();
        }

        wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();

        esp_wifi_init(&cfg);

        esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &eventHandler, nullptr);

        if (!apMode)
        {
            esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &eventHandler, nullptr);
        }

        wifi_config_t wifiConfig = {};

        if (apMode)
        {

            strncpy(reinterpret_cast<char *>(wifiConfig.ap.ssid), ssid.c_str(), sizeof(wifiConfig.ap.ssid));

            strncpy(reinterpret_cast<char *>(wifiConfig.ap.password), password.c_str(), sizeof(wifiConfig.ap.password));

            wifiConfig.ap.ssid_len = ssid.size();

            wifiConfig.ap.channel = AP_CHANNEL;

            wifiConfig.ap.max_connection = AP_MAX_CONN;

            wifiConfig.ap.authmode = !password.empty() ? WIFI_AUTH_WPA2_PSK : WIFI_AUTH_OPEN;
            esp_wifi_set_mode(WIFI_MODE_AP);
            esp_wifi_set_config(WIFI_IF_AP, &wifiConfig);
            esp_wifi_set_ps(WIFI_PS_NONE);

            ESP_LOGI(TAG, "Configured AP mode. SSID: %s", ssid.c_str());
        }
        else
        {
            strncpy(reinterpret_cast<char *>(wifiConfig.sta.ssid), ssid.c_str(), sizeof(wifiConfig.sta.ssid));

            strncpy(reinterpret_cast<char *>(wifiConfig.sta.password), password.c_str(), sizeof(wifiConfig.sta.password));

            wifiConfig.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;

            wifiConfig.sta.pmf_cfg.capable = true;
            wifiConfig.sta.pmf_cfg.required = false;

            esp_wifi_set_mode(WIFI_MODE_STA);
            esp_wifi_set_config(WIFI_IF_STA, &wifiConfig);
            ESP_LOGI(TAG, "Configured AP mode. SSID: %s", ssid.c_str());
        }

        isInitialized = true;
        start();

        ESP_LOGI(TAG, "WiFi initialization complete (%s)", apMode ? "AP" : "STA");
    }

    void deinit()
    {
        if (!isInitialized)
        {
            ESP_LOGW(TAG, "WiFi not initialized");
            return;
        }

        ESP_LOGI(TAG, "Deinitializing WiFiService...");

        stop();

        esp_wifi_disconnect();

        esp_event_handler_unregister(WIFI_EVENT, ESP_EVENT_ANY_ID, &eventHandler);
        esp_event_handler_unregister(IP_EVENT, IP_EVENT_STA_GOT_IP, &eventHandler);

        esp_wifi_deinit();

        if (staNetif)
        {
            esp_netif_destroy(staNetif);
            staNetif = nullptr;
        }

        if (apNetif)
        {
            esp_netif_destroy(apNetif);
            apNetif = nullptr;
        }

        if (eventGroup)
        {
            vEventGroupDelete(eventGroup);
            eventGroup = nullptr;
        }

        isInitialized = false;
        wifiStarted = false;
        isInAPMode = false;

        strcpy(ipAddress, "0.0.0.0");
        rssi = 0;

        ESP_LOGI(TAG, "WiFiService deinitialized");
    }

    bool start()
    {
        if (!isInitialized)
        {
            ESP_LOGW(TAG, "WiFi not initialized");
            return false;
        }

        if (wifiStarted)
        {
            ESP_LOGD(TAG, "WiFi already started");
            return true;
        }

        esp_err_t err = esp_wifi_start();

        if (err != ESP_OK)
        {
            ESP_LOGE(TAG, "Failed to start WiFi: %s", esp_err_to_name(err));
            return false;
        }

        wifiStarted = true;

        if (isInAPMode)
        {
            strcpy(ipAddress, "192.168.4.1");

            if (eventGroup)
            {
                xEventGroupSetBits(eventGroup, WIFI_CONNECTED_BIT);
            }
        }

        ESP_LOGI(TAG, "WiFi started");

        return true;
    }

    bool stop()
    {
        if (!isInitialized)
        {
            ESP_LOGW(TAG, "WiFi not initialized");
            return false;
        }

        if (!wifiStarted)
        {
            ESP_LOGD(TAG, "WiFi already stopped");
            return true;
        }

        esp_err_t err = esp_wifi_stop();

        if (err != ESP_OK)
        {
            ESP_LOGE(TAG, "Failed to stop WiFi: %s", esp_err_to_name(err));
            return false;
        }

        wifiStarted = false;

        //
        // Clear connection state
        //
        if (eventGroup)
        {
            xEventGroupClearBits(eventGroup, WIFI_CONNECTED_BIT);
        }

        strcpy(ipAddress, "0.0.0.0");

        rssi = 0;

        ESP_LOGI(TAG, "WiFi stopped");

        return true;
    }

    bool isConnected()
    {

        if (!isInitialized || !eventGroup)
        {
            return false;
        }

        return (
                   xEventGroupGetBits(eventGroup) &
                   WIFI_CONNECTED_BIT) != 0;
    }

    const char *getStatusString()
    {

        if (!isInitialized)
        {
            return "Not Initialized";
        }

        if (isInAPMode)
        {
            return "AP Running";
        }

        return isConnected()
                   ? "Connected"
                   : "Disconnected";
    }

    void reconnect()
    {

        if (isInAPMode)
        {
            ESP_LOGW(TAG, "Reconnect ignored in AP mode");
            return;
        }

        if (!isInitialized)
        {
            ESP_LOGW(TAG, "Cannot reconnect - WiFi not initialized");
            return;
        }

        ESP_LOGI(TAG, "Manual reconnection triggered");

        if (isConnected())
        {
            esp_wifi_disconnect();
        }

        esp_wifi_connect();
    }

    const char *getIPAddress()
    {
        return ipAddress;
    }

    int getRSSI()
    {
        if (isInAPMode)
        {
            return 0;
        }

        if (!isConnected())
        {
            return 0;
        }

        wifi_ap_record_t apInfo;

        if (esp_wifi_sta_get_ap_info(&apInfo) == ESP_OK)
        {
            rssi = apInfo.rssi;
        }

        return rssi;
    }
}