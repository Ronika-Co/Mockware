#pragma once
#include <cstdint>
#include <functional>
#include <string>

namespace TimerAdapter {
    using Callback = std::function<void()>;

    void startOnce(const std::string &name, uint64_t delayMs, Callback cb);

    void stop(const std::string &name);

    void stopAll();
}
