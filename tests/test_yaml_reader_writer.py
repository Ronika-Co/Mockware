import tempfile
from pathlib import Path

import yaml

from mockware.parser.yaml_writer import write_yaml
from mockware.generator.yaml_reader import read_yaml


SAMPLE_DATA: dict[str, dict] = {
    "esp_err.h": {
        "includes": [],
        "macros": {"ESP_OK": "0", "ESP_FAIL": "-1"},
        "types": {"esp_err_t": "int"},
        "enums": {},
        "structs": {},
        "functions": {
            "esp_err_to_name": {
                "return": "const char*",
                "params": ["esp_err_t err"],
            }
        },
    },
    "driver/gpio.h": {
        "includes": ["esp_err.h"],
        "macros": {"GPIO_NUM_0": "0"},
        "types": {"gpio_num_t": "int"},
        "enums": {
            "gpio_mode_t": {"values": {"GPIO_MODE_INPUT": 0, "GPIO_MODE_OUTPUT": 1}}
        },
        "structs": {
            "gpio_config_t": {
                "definition": "typedef struct { uint64_t pin_bit_mask; } gpio_config_t;"
            }
        },
        "functions": {
            "gpio_set_direction": {
                "return": "esp_err_t",
                "params": ["gpio_num_t gpio_num", "gpio_mode_t mode"],
            }
        },
    },
}


def test_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        yaml_path = Path(tmp) / "test.yml"
        write_yaml(SAMPLE_DATA, str(yaml_path))

        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert "headers" in raw
        assert "esp_err.h" in raw["headers"]

        loaded = read_yaml(str(yaml_path))
        assert loaded["esp_err.h"]["macros"]["ESP_OK"] == "0"
        assert loaded["driver/gpio.h"]["includes"] == ["esp_err.h"]
        assert (
            loaded["driver/gpio.h"]["functions"]["gpio_set_direction"]["return"]
            == "esp_err_t"
        )


def test_normalises_missing_keys() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        yaml_path = Path(tmp) / "partial.yml"
        minimal = {"headers": {"empty.h": None}}
        yaml_path.write_text(yaml.dump(minimal))

        loaded = read_yaml(str(yaml_path))
        assert "empty.h" in loaded
        entry = loaded["empty.h"]
        assert entry["includes"] == []
        assert entry["macros"] == {}
        assert entry["functions"] == {}
