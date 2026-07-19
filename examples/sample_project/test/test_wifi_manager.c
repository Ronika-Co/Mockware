#include <assert.h>
#include <stdio.h>
#include "wifi_manager.h"
#include "mockware/fakes.h"

/* ── Custom fakes ── */

static esp_err_t mock_nvs_flash_init(void)
{
    return ESP_OK;
}

static esp_err_t mock_wifi_start_fail(void)
{
    return ESP_FAIL;
}

static esp_err_t mock_wifi_start_ok(void)
{
    return ESP_OK;
}

static esp_err_t mock_wifi_stop_ok(void)
{
    return ESP_OK;
}

/* ── Tests ── */

static void test_wifi_manager_start_success(void)
{
    printf("test: wifi_manager_start returns OK when all deps succeed...\n");

    nvs_flash_init_mock = mock_nvs_flash_init;
    esp_wifi_start_mock = mock_wifi_start_ok;

    assert(wifi_manager_start() == WIFI_MGR_OK);
    printf("  PASSED\n");
}

static void test_wifi_manager_start_wifi_fail(void)
{
    printf("test: wifi_manager_start returns FAIL when esp_wifi_start fails...\n");

    nvs_flash_init_mock = mock_nvs_flash_init;
    esp_wifi_start_mock = mock_wifi_start_fail;

    assert(wifi_manager_start() == WIFI_MGR_FAIL);
    printf("  PASSED\n");
}

static void test_wifi_manager_stop(void)
{
    printf("test: wifi_manager_stop returns OK...\n");

    esp_wifi_stop_mock = mock_wifi_stop_ok;
    assert(wifi_manager_stop() == WIFI_MGR_OK);
    printf("  PASSED\n");
}

int main(void)
{
    test_wifi_manager_start_success();
    test_wifi_manager_start_wifi_fail();
    test_wifi_manager_stop();

    printf("\nAll tests passed!\n");
    return 0;
}
