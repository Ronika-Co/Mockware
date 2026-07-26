from pathlib import Path

from mockware.generator.source_gen import generate_sources
from mockware.yaml_reader import read_config


def _read_and_gen(samples_dir: Path, output_dir: Path, name: str):
    config = read_config(samples_dir / name)
    generate_sources(str(output_dir), config)
    return config, output_dir


def test_c_source_basic(samples_dir: Path, tmp_output: Path):
    config, out = _read_and_gen(samples_dir, tmp_output, "basic_c.yml")

    gpio_src = out / "source" / "driver" / "gpio.c"
    assert gpio_src.exists()
    content = gpio_src.read_text()

    assert '#include "driver/gpio.h"' in content
    assert '#include "mockware/fakes.h"' in content

    assert "static esp_err_t gpio_set_level_default(int pin, int level)" in content
    assert "return ESP_OK;" in content
    assert "esp_err_t (*gpio_set_level_mock)(int pin, int level)" in content
    assert "return gpio_set_level_mock(pin, level);" in content

    assert "static int gpio_get_level_default(int pin)" in content
    assert "return 0;" in content
    assert "int (*gpio_get_level_mock)(int pin)" in content

    task_src = out / "source" / "freertos" / "task.c"
    assert task_src.exists()
    content = task_src.read_text()
    assert "vTaskDelay_default" in content
    assert "vTaskDelay_mock" in content


def test_cpp_source_basic(samples_dir: Path, tmp_output: Path):
    config, out = _read_and_gen(samples_dir, tmp_output, "basic_cpp.yml")

    src = out / "source" / "device" / "sensor.cpp"
    assert src.exists()
    content = src.read_text()

    assert '#include "device/sensor.hpp"' in content
    assert '#include "mockware/fakes.h"' in content
    assert "sensor_isr_handler_default" in content
    assert "sensor_isr_handler_mock" in content

    # function pointer params should extract cb correctly
    assert "sensor_isr_handler_mock(irq, callback);" in content


def test_no_source_for_no_funcs(samples_dir: Path, tmp_output: Path):
    """Headers with no functions should not produce source files."""
    config, out = _read_and_gen(samples_dir, tmp_output, "basic_c.yml")

    esp_err_src = out / "source" / "esp_err.c"
    assert not esp_err_src.exists()
