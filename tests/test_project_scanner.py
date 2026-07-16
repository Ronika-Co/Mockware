import tempfile
from pathlib import Path

from mockware.generator.project_scanner import find_used_headers


def test_finds_simple_include() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        main_c = Path(tmp) / "main.c"
        main_c.write_text('#include "driver/gpio.h"\n')
        used = find_used_headers(tmp, verbose=False)
        assert used == {"driver/gpio.h"}


def test_finds_multiple_includes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "app.c"
        src.write_text(
            '#include "esp_wifi.h"\n#include "nvs_flash.h"\n#include "esp_err.h"\n'
        )
        used = find_used_headers(tmp, verbose=False)
        assert used == {"esp_wifi.h", "nvs_flash.h", "esp_err.h"}


def test_finds_includes_across_multiple_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "a.c").write_text('#include "driver/gpio.h"\n')
        (Path(tmp) / "b.c").write_text('#include "freertos/FreeRTOS.h"\n')
        used = find_used_headers(tmp, verbose=False)
        assert used == {"driver/gpio.h", "freertos/FreeRTOS.h"}


def test_scans_subdirectories() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        sub = Path(tmp) / "sub" / "nested"
        sub.mkdir(parents=True)
        (sub / "code.c").write_text('#include "esp_ota_ops.h"\n')
        used = find_used_headers(tmp, verbose=False)
        assert used == {"esp_ota_ops.h"}


def test_ignores_non_esp_includes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "main.c").write_text(
            '#include <stdio.h>\n#include "my_local.h"\n'
        )
        used = find_used_headers(tmp, verbose=False)
        assert used == set()


def test_handles_empty_directories() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        used = find_used_headers(tmp, verbose=False)
        assert used == set()
