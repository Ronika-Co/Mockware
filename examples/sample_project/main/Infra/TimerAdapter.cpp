#include "TimerAdapter.h"
#include "esp_timer.h"
#include <map>
#include <string>

namespace TimerAdapter {
    struct TimerEntry {
        esp_timer_handle_t handle;
        Callback callback;
    };

    static std::map<std::string, TimerEntry> timers;

    static void internalCallback(void *arg) {
        const auto key = static_cast<std::string *>(arg);

        const auto it = timers.find(*key);
        if (it == timers.end()) {
            delete key;
            return;
        }

        auto cb = std::move(it->second.callback);
        timers.erase(it);
        delete key;

        if (cb) {
            cb();
        }
    }

    void startOnce(const std::string &name, const uint64_t delayMs, Callback cb) {
        stop(name);

        auto *keyCopy = new std::string(name);

        esp_timer_create_args_t args{};
        args.callback = &internalCallback;
        args.arg = keyCopy;
        args.dispatch_method = ESP_TIMER_TASK;
        args.name = name.c_str();

        esp_timer_handle_t handle;
        const auto err = esp_timer_create(&args, &handle);
        if (err != ESP_OK) {
            delete keyCopy;
            return;
        }

        const auto errStart = esp_timer_start_once(handle, delayMs * 1000);
        if (errStart != ESP_OK) {
            esp_timer_delete(handle);
            delete keyCopy;
            return;
        }

        timers[name] = {handle, std::move(cb)};
    }

    void stop(const std::string &name) {
        const auto it = timers.find(name);
        if (it == timers.end()) {
            return;
        }
        esp_timer_stop(it->second.handle);
        esp_timer_delete(it->second.handle);
        timers.erase(it);
    }

    void stopAll() {
        for (auto &[name, entry] : timers) {
            esp_timer_stop(entry.handle);
            esp_timer_delete(entry.handle);
        }
        timers.clear();
    }
}
