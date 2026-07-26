#pragma once

#include <stdint.h>

namespace OpenThreadService {
    static constexpr auto TAG = "OpenThreadService";

    void taskHandler(void *aContext);

    uint32_t getDisconnectedCount();

    bool stop();

    bool start();
}
