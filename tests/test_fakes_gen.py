from pathlib import Path

from mockware.generator.fakes_gen import generate_fakes_header
from mockware.yaml_reader import read_config


def _read_and_gen(samples_dir: Path, output_dir: Path, name: str):
    config = read_config(samples_dir / name)
    generate_fakes_header(str(output_dir), config)
    return config, output_dir


def test_fakes_basic_c(samples_dir: Path, tmp_output: Path):
    _, out = _read_and_gen(samples_dir, tmp_output, "basic_c.yml")

    fakes = out / "include" / "mockware" / "fakes.h"
    assert fakes.exists()
    content = fakes.read_text()

    assert "#pragma once" in content
    assert "extern esp_err_t (*gpio_set_level_mock)(int pin, int level);" in content
    assert "extern int (*gpio_get_level_mock)(int pin);" in content
    assert "extern void (*vTaskDelay_mock)(int ticks);" in content


def test_fakes_basic_cpp(samples_dir: Path, tmp_output: Path):
    _, out = _read_and_gen(samples_dir, tmp_output, "basic_cpp.yml")

    fakes = out / "include" / "mockware" / "fakes.h"
    assert fakes.exists()
    content = fakes.read_text()

    assert "extern void (*sensor_isr_handler_mock)(int irq, void (*callback)(void*));" in content
