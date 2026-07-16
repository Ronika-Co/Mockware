from __future__ import annotations

import os
import re
from pathlib import Path

import click

_ESP_INCLUDE_RE = re.compile(
    r'#include\s+[<"]'             # #include < or "
    r'((?:esp|freertos|driver|hal|soc|esp_|nvs|tcpip|mdns|mqtt|http|periph|rom|xtensa|riscv|newlib|sdkconfig)[^>"]+)'
    r'[>"]'
)


def find_used_headers(project_path: str, verbose: bool) -> set[str]:
    """Recursively scan *project_path* for ESP-IDF #include directives.

    Returns a set of header paths as they appear in includes
    (e.g. ``{"driver/gpio.h", "freertos/FreeRTOS.h", "esp_err.h"}``).
    """
    used: set[str] = set()
    src_extensions = {".c", ".h", ".cpp", ".hpp", ".cc", ".cxx"}

    for root, _dirs, files in os.walk(project_path):
        for fname in files:
            ext = Path(fname).suffix
            if ext not in src_extensions:
                continue
            fpath = Path(root) / fname
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            for match in _ESP_INCLUDE_RE.finditer(text):
                include_path = match.group(1)
                used.add(include_path)

            if verbose:
                click.echo(f"    scanned {fname}")

    return used
