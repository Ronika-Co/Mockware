import tempfile
from pathlib import Path

from mockware.generator.fakes_header_gen import generate_fakes_header

DATA_WITH_FUNCS: dict = {
    "headers": {
        "esp_wifi.h": {"includes": []},
        "esp_err.h": {"includes": []},
    },
    "types": {"esp_err_t": "int"},
    "macros": {"ESP_OK": "0"},
    "enums": {},
    "structs": {},
    "functions": {
        "esp_wifi_start": {"return": "esp_err_t", "params": [],
                           "header": "esp_wifi.h"},
        "esp_wifi_stop": {"return": "esp_err_t", "params": [],
                          "header": "esp_wifi.h"},
        "esp_err_to_name": {"return": "const char*",
                            "params": ["esp_err_t err"],
                            "header": "esp_err.h"},
    },
}

DATA_EMPTY: dict = {
    "headers": {},
    "types": {},
    "macros": {},
    "enums": {},
    "structs": {},
    "functions": {},
}


def test_generates_fakes_header() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        generate_fakes_header(str(out), DATA_WITH_FUNCS, verbose=False)
        assert (out / "include" / "mockware" / "fakes.h").exists()


def test_all_functions_in_one_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        generate_fakes_header(str(out), DATA_WITH_FUNCS, verbose=False)
        content = (out / "include" / "mockware" / "fakes.h").read_text()
        assert "esp_wifi_start_mock" in content
        assert "esp_wifi_stop_mock" in content
        assert "esp_err_to_name_mock" in content


def test_extern_declaration_format() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        generate_fakes_header(str(out), DATA_WITH_FUNCS, verbose=False)
        content = (out / "include" / "mockware" / "fakes.h").read_text()
        assert "extern esp_err_t (*esp_wifi_start_mock)(void);" in content


def test_cpp_guard() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        generate_fakes_header(str(out), DATA_WITH_FUNCS, verbose=False)
        content = (out / "include" / "mockware" / "fakes.h").read_text()
        assert "#ifdef __cplusplus" in content
        assert 'extern "C" {' in content
        assert '} /* extern "C" */' in content


def test_skips_inline_functions() -> None:
    data = {
        "headers": {},
        "types": {},
        "macros": {},
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
    }
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        generate_fakes_header(str(out), data, verbose=False)
        content = (out / "include" / "mockware" / "fakes.h").read_text()
        assert "bar_mock" not in content
        assert "baz_mock" in content


def test_includes_defs_headers() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        generate_fakes_header(str(out), DATA_WITH_FUNCS, verbose=False)
        content = (out / "include" / "mockware" / "fakes.h").read_text()
        assert '#include "mockware/types.h"' in content
        assert '#include "mockware/macros.h"' in content
        assert '#include "mockware/enums.h"' in content
        assert '#include "mockware/structs.h"' in content


def test_skips_empty() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        generate_fakes_header(str(out), DATA_EMPTY, verbose=False)
        assert not (out / "include" / "mockware" / "fakes.h").exists()
