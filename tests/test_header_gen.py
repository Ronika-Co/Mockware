from pathlib import Path

from mockware.generator.header_gen import generate_headers
from mockware.yaml_reader import read_config


def _read_and_gen(samples_dir: Path, output_dir: Path, name: str):
    config = read_config(samples_dir / name)
    generate_headers(str(output_dir), config)
    return config, output_dir


def test_c_header_basic(samples_dir: Path, tmp_output: Path):
    config, out = _read_and_gen(samples_dir, tmp_output, "basic_c.yml")

    esp_err_path = out / "include" / "esp_err.h"
    assert esp_err_path.exists()
    content = esp_err_path.read_text()
    assert "#pragma once" in content
    assert "#define ESP_OK 0" in content
    assert "#define ESP_FAIL -1" in content
    assert "typedef int esp_err_t;" in content

    gpio_path = out / "include" / "driver" / "gpio.h"
    assert gpio_path.exists()
    content = gpio_path.read_text()
    assert '#include "esp_err.h"' in content
    assert "#define GPIO_OUT 1" in content
    assert "typedef int gpio_mode_t;" in content
    assert "esp_err_t gpio_set_level(int pin, int level);" in content
    assert "int gpio_get_level(int pin);" in content

    task_path = out / "include" / "freertos" / "task.h"
    assert task_path.exists()
    content = task_path.read_text()
    assert "#define pdMS_TO_TICKS(...) ((x) / portTICK_PERIOD_MS)" in content
    assert "void vTaskDelay(int ticks);" in content


def test_cpp_header_basic(samples_dir: Path, tmp_output: Path):
    config, out = _read_and_gen(samples_dir, tmp_output, "basic_cpp.yml")

    hpp_path = out / "include" / "device" / "sensor.hpp"
    assert hpp_path.exists()
    content = hpp_path.read_text()

    assert "#pragma once" in content
    assert "#include <cstdint>" in content
    assert "typedef int sensor_err_t;" in content
    assert "typedef enum {" in content
    assert "SENSOR_MODE_SLEEP = 0," in content
    assert "SENSOR_MODE_ACTIVE = 1," in content
    assert "} sensor_mode_t;" in content

    assert "namespace drivers {" in content
    assert "class TemperatureSensor {" in content
    assert "TemperatureSensor(int pin) : pin_(pin) {}" in content
    assert "virtual ~TemperatureSensor() = default;" in content
    assert "virtual float read(void) { return 25.0f; }" in content
    assert "virtual sensor_err_t calibrate(void) { return 0; }" in content
    assert "static float get_reference_voltage(void) { return 3.3f; }" in content

    assert "protected:" in content
    assert "int pin_;" in content
    assert "float last_value_;" in content

    assert "void sensor_isr_handler(int irq, void (*callback)(void*));" in content
    assert "}  // namespace drivers" in content
