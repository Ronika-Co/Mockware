import tempfile
from pathlib import Path

from mockware.generator.fakes_header_gen import generate_fakes_headers

APIS = {
    "esp_err.h": {
        "includes": [],
        "macros": {"ESP_OK": "0"},
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
    "esp_wifi.h": {
        "includes": ["esp_err.h"],
        "macros": {},
        "types": {},
        "enums": {},
        "structs": {},
        "functions": {
            "esp_wifi_start": {"return": "esp_err_t", "params": []},
            "esp_wifi_stop": {"return": "esp_err_t", "params": []},
        },
    },
    "esp_wifi_types.h": {
        "includes": ["esp_err.h"],
        "macros": {"WIFI_MODE_STA": "0"},
        "types": {},
        "enums": {
            "wifi_mode_t": {
                "values": {"WIFI_MODE_NULL": 0, "WIFI_MODE_STA": 1}
            }
        },
        "structs": {},
        "functions": {
            "esp_wifi_set_mode": {
                "return": "esp_err_t",
                "params": ["wifi_mode_t mode"],
            }
        },
    },
    "driver/gpio.h": {
        "includes": ["esp_err.h"],
        "macros": {},
        "types": {"gpio_num_t": "int"},
        "enums": {},
        "structs": {},
        "functions": {
            "gpio_set_direction": {
                "return": "esp_err_t",
                "params": ["gpio_num_t gpio_num", "gpio_mode_t mode"],
            }
        },
    },
    "nvs_flash.h": {
        "includes": ["esp_err.h"],
        "macros": {},
        "types": {},
        "enums": {},
        "structs": {},
        "functions": {
            "nvs_flash_init": {"return": "esp_err_t", "params": []},
        },
    },
}


def test_generates_fakes_per_component() -> None:
    """Two headers from same component → one merged file."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        used = {"esp_wifi.h", "esp_wifi_types.h", "esp_err.h", "nvs_flash.h"}
        generate_fakes_headers(str(out), APIS, used, verbose=False)

        # Merged into one file per component
        assert (out / "include" / "esp_wifi_fakes.h").exists()
        assert (out / "include" / "esp_err_fakes.h").exists()
        assert (out / "include" / "nvs_flash_fakes.h").exists()

        content = (out / "include" / "esp_wifi_fakes.h").read_text()
        assert "esp_wifi_start_fp" in content
        assert "esp_wifi_stop_fp" in content
        assert "esp_wifi_set_mode_fp" in content


def test_driver_header_uses_path_segment() -> None:
    """driver/gpio.h → driver_fakes.h"""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        used = {"driver/gpio.h", "esp_err.h"}
        generate_fakes_headers(str(out), APIS, used, verbose=False)

        assert (out / "include" / "driver_fakes.h").exists()
        content = (out / "include" / "driver_fakes.h").read_text()
        assert "gpio_set_direction_fp" in content


def test_extern_declaration_format() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        used = {"esp_wifi.h"}
        generate_fakes_headers(str(out), APIS, used, verbose=False)

        content = (out / "include" / "esp_wifi_fakes.h").read_text()
        assert "extern esp_err_t (*esp_wifi_start_fp)(void);" in content


def test_cpp_guard() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        used = {"esp_wifi.h"}
        generate_fakes_headers(str(out), APIS, used, verbose=False)

        content = (out / "include" / "esp_wifi_fakes.h").read_text()
        assert "#ifdef __cplusplus" in content
        assert 'extern "C" {' in content
        assert '} /* extern "C" */' in content


def test_skips_inline_functions() -> None:
    apis = {
        "foo.h": {
            "includes": [],
            "macros": {},
            "types": {},
            "enums": {},
            "structs": {},
            "functions": {
                "bar": {
                    "kind": "inline",
                    "return": "void",
                    "params": [],
                    "body": "static inline void bar(void) {}",
                },
                "baz": {"return": "int", "params": []},
            },
        },
    }
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        generate_fakes_headers(str(out), apis, {"foo.h"}, verbose=False)

        content = (out / "include" / "foo_fakes.h").read_text()
        assert "bar_fp" not in content
        assert "baz_fp" in content


def test_skips_empty_components() -> None:
    """Component with only inline functions → no file generated."""
    apis = {
        "empty.h": {
            "includes": [],
            "macros": {},
            "types": {},
            "enums": {},
            "structs": {},
            "functions": {
                "e": {
                    "kind": "inline",
                    "return": "void",
                    "params": [],
                    "body": "",
                }
            },
        },
    }
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        used = {"empty.h"}
        generate_fakes_headers(str(out), apis, used, verbose=False)
        assert not (out / "include" / "empty_fakes.h").exists()


def test_skips_header_not_in_apis() -> None:
    """Unknown header in used set → silently skipped."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        used = {"esp_wifi.h", "unknown.h"}
        generate_fakes_headers(str(out), APIS, used, verbose=False)
        # Only known headers produce files
        assert (out / "include" / "esp_wifi_fakes.h").exists()
        assert not (out / "include" / "unknown_fakes.h").exists()
