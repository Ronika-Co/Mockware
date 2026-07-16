#pragma once

typedef enum {
    WIFI_MGR_OK = 0,
    WIFI_MGR_FAIL = -1,
} wifi_mgr_status_t;

wifi_mgr_status_t wifi_manager_start(void);
wifi_mgr_status_t wifi_manager_stop(void);
