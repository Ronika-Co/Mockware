#include "OpenThreadService.h"

#include "ConfigStorage.h"
#include "esp_netif.h"
#include "esp_netif_types.h"
#include "esp_openthread.h"
#include "esp_openthread_cli.h"
#include "esp_openthread_netif_glue.h"
#include "esp_vfs_eventfd.h"
#include "openthread/logging.h"
#include "freertos/task.h"
#include <openthread/dataset.h>

#include "esp_event.h"
#include "NetworkService.h"
#include "Support.h"
#include "openthread/thread_ftd.h"
#include "openthread/ip6.h"

namespace OpenThreadService
{

    static esp_netif_t *network_interface;
    static uint32_t disconnect_count = 0;
    static otDeviceRole previous_role = OT_DEVICE_ROLE_DISABLED;

    static esp_err_t init_network_interface(const esp_openthread_platform_config_t *config)
    {
        constexpr esp_netif_config_t netIfConfig = ESP_NETIF_DEFAULT_OPENTHREAD();
        network_interface = esp_netif_new(&netIfConfig);
        assert(network_interface != nullptr);
        const auto res = esp_netif_attach(network_interface, esp_openthread_netif_glue_init(config));
        if (res != ESP_OK)
        {
            ESP_LOGE(TAG, "esp_netif_attach failed: %s", esp_err_to_name(res));
        }
        return res;
    }

    static void stateChangedEvent(otChangedFlags flags, void *context)
    {
        otInstance *instance = esp_openthread_get_instance();
        const otDeviceRole role = otThreadGetDeviceRole(instance);

        if ((role == OT_DEVICE_ROLE_DETACHED || role == OT_DEVICE_ROLE_DISABLED) &&
            (previous_role != OT_DEVICE_ROLE_DETACHED && previous_role != OT_DEVICE_ROLE_DISABLED))
        {
            disconnect_count++;
            esp_event_post(NETWORK_EVENT, NETWORK_EVENT_DISCONNECTED, nullptr, 0, portMAX_DELAY);
            ESP_LOGD(TAG, "Disconnected from Thread network (count=%lu)", disconnect_count);
        }
        previous_role = role;

        if ((role == OT_DEVICE_ROLE_CHILD || role == OT_DEVICE_ROLE_ROUTER || role == OT_DEVICE_ROLE_LEADER))
        {
            esp_event_post(NETWORK_EVENT, NETWORK_EVENT_CONNECTED, nullptr, 0, portMAX_DELAY);
        }
    }

    static esp_openthread_platform_config_t openThreadConfig()
    {
        esp_openthread_radio_config_t radioConfig = {};
        radioConfig.radio_mode = RADIO_MODE_NATIVE;

        esp_openthread_host_connection_config_t hostConfig = {};
        hostConfig.host_connection_mode = HOST_CONNECTION_MODE_CLI_UART;
        hostConfig.host_uart_config.port = UART_NUM_0;

        uart_config_t uartConfig = {};
        uartConfig.baud_rate = 115200;
        uartConfig.data_bits = UART_DATA_8_BITS;
        uartConfig.parity = UART_PARITY_DISABLE;
        uartConfig.stop_bits = UART_STOP_BITS_1;
        uartConfig.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
        uartConfig.rx_flow_ctrl_thresh = 0;
        uartConfig.source_clk = UART_SCLK_DEFAULT;
        hostConfig.host_uart_config.uart_config = uartConfig;

        hostConfig.host_uart_config.rx_pin = GPIO_NUM_NC;
        hostConfig.host_uart_config.tx_pin = GPIO_NUM_NC;

        esp_openthread_port_config_t portConfig = {};

        portConfig.storage_partition_name = "nvs";
        portConfig.netif_queue_size = 10;
        portConfig.task_queue_size = 10;

        esp_openthread_platform_config_t config = {};
        config.radio_config = radioConfig;
        config.host_config = hostConfig;
        config.port_config = portConfig;
        return config;
    }

    static bool hexStringToBytes(const std::string &hex, uint8_t *out, size_t outSize)
    {
        if (hex.length() < 2 * outSize)
            return false;
        for (size_t i = 0; i < outSize; ++i)
        {
            char high = hex[2 * i];
            char low = hex[2 * i + 1];
            auto nibble = [](char c) -> int
            {
                if (c >= '0' && c <= '9')
                    return c - '0';
                if (c >= 'a' && c <= 'f')
                    return c - 'a' + 10;
                if (c >= 'A' && c <= 'F')
                    return c - 'A' + 10;
                return -1;
            };
            int h = nibble(high), l = nibble(low);
            if (h < 0 || l < 0)
                return false;
            out[i] = (h << 4) | l;
        }
        return true;
    }

    bool setupOpenThread()
    {
        // Initialize the OpenThread stack
        const auto config = openThreadConfig();
        ESP_ERROR_CHECK(esp_openthread_init(&config));

        // The OpenThread log level directly matches ESP log level
        (void)otLoggingSetLevel(CONFIG_LOG_DEFAULT_LEVEL);

        // Initialize the OpenThread cli
        esp_openthread_cli_init();

        // Initialize the network interface bindings
        init_network_interface(&config);
        esp_netif_set_default_netif(network_interface);

        esp_openthread_cli_create_task();

        const auto connectionConfig = ConfigStorage::readConnectionConfig();

        ESP_LOGI(TAG, "openthread network name: %s - openthread network key: %s", connectionConfig.ssid.c_str(),
                 connectionConfig.password.c_str());

        otInstance *instance = esp_openthread_get_instance();

        otOperationalDataset dataset = {};
        const bool hasActiveDataset = otDatasetGetActive(instance, &dataset) == OT_ERROR_NONE;

        auto networkNameMatches = [&]()
        {
            return strcmp(dataset.mNetworkName.m8, connectionConfig.ssid.c_str()) == 0;
        };

        auto networkKeyMatches = [&]()
        {
            otNetworkKey expected = {};
            if (!hexStringToBytes(connectionConfig.password, expected.m8, sizeof(expected.m8)))
            {
                return false; // invalid hex → force update
            }
            return memcmp(dataset.mNetworkKey.m8, expected.m8, OT_NETWORK_KEY_SIZE) == 0;
        };

        if (!hasActiveDataset || !networkNameMatches() || !networkKeyMatches())
        {
            ESP_LOGI(TAG, "No active dataset found, creating new network using SSID/PSK");

            otNetworkName networkName = {};
            strncpy(networkName.m8, connectionConfig.ssid.c_str(), OT_NETWORK_NAME_MAX_SIZE);
            dataset.mNetworkName = networkName;
            dataset.mComponents.mIsNetworkNamePresent = true;

            otNetworkKey networkKey = {};
            if (!hexStringToBytes(connectionConfig.password, networkKey.m8, sizeof(networkKey.m8)))
            {
                ESP_LOGE(TAG, "Invalid hex key");
                return false;
            }
            dataset.mNetworkKey = networkKey; // ← THIS LINE WAS MISSING!
            dataset.mComponents.mIsNetworkKeyPresent = true;

            const auto err = otDatasetSetActive(instance, &dataset);
            if (err != OT_ERROR_NONE)
            {
                ESP_LOGE(TAG, "otDatasetSetActive failed: %s", otThreadErrorToString(err));
                return err;
            }
            ESP_LOGI(TAG, "New Thread network created and activated");
        }
        else
        {
            ESP_LOGI(TAG, "Existing active dataset found, joining network");
        }

        otOperationalDatasetTlvs datasetTlvs;
        otDatasetConvertToTlvs(&dataset, &datasetTlvs);

        const auto res = esp_openthread_auto_start(&datasetTlvs);
        if (res != ESP_OK)
        {
            ESP_LOGE(TAG, "esp_openthread_auto_start failed: %s", esp_err_to_name(res));
            return false;
        }

        // Register OpenThread state change callback (if not already done elsewhere)
        otSetStateChangedCallback(esp_openthread_get_instance(),
                                  stateChangedEvent, nullptr);
        return true;
    }

    void taskHandler(void *aContext)
    {
        setupOpenThread();
        esp_openthread_launch_mainloop();

        // Clean up
        esp_openthread_netif_glue_deinit();
        esp_netif_destroy(network_interface);

        esp_vfs_eventfd_unregister();
        vTaskDelete(nullptr);
    }

    uint32_t getDisconnectedCount()
    {
        return disconnect_count;
    }

    bool stop()
    {
        otInstance *instance = esp_openthread_get_instance();
        if (!instance)
        {
            ESP_LOGW(TAG, "OpenThread instance not available");
            return false;
        }
        // otIfConfigDown(instance);
        const otError err = otThreadSetEnabled(instance, false);
        if (err != OT_ERROR_NONE)
        {
            ESP_LOGE(TAG, "Failed to stop OpenThread: %s", otThreadErrorToString(err));
            return false;
        }
        ESP_LOGI(TAG, "OpenThread stopped");
        return true;
    }

    bool start()
    {
        otInstance *instance = esp_openthread_get_instance();
        if (!instance)
        {
            ESP_LOGW(TAG, "OpenThread instance not available");
            return false;
        }
        // otIfConfigUp(instance);
        const otError err = otThreadSetEnabled(instance, true);
        if (err != OT_ERROR_NONE)
        {
            ESP_LOGE(TAG, "Failed to start OpenThread: %s", otThreadErrorToString(err));
            return false;
        }
        ESP_LOGI(TAG, "OpenThread started");
        return true;
    }
}
