import tempfile
from pathlib import Path

from mockware.generator.defs_header_gen import (
    generate_defs_headers,
    needed_standard_includes,
)


def test_std_includes_empty_when_no_std_types() -> None:
    data: dict = {
        "headers": {},
        "types": {"esp_err_t": "int"},
        "macros": {"ESP_OK": "0"},
        "enums": {},
        "structs": {},
        "functions": {},
    }
    assert needed_standard_includes(data) == set()


def test_std_includes_from_type_underlying() -> None:
    data: dict = {
        "headers": {},
        "types": {"my_time": "uint64_t"},
        "macros": {},
        "enums": {},
        "structs": {},
        "functions": {},
    }
    assert "<stdint.h>" in needed_standard_includes(data)


def test_std_includes_from_function_params() -> None:
    data: dict = {
        "headers": {},
        "types": {},
        "macros": {},
        "enums": {},
        "structs": {},
        "functions": {
            "wait_ms": {"return": "void", "params": ["uint64_t ms"]},
        },
    }
    assert "<stdint.h>" in needed_standard_includes(data)


def test_std_includes_from_function_return() -> None:
    data: dict = {
        "headers": {},
        "types": {},
        "macros": {},
        "enums": {},
        "structs": {},
        "functions": {
            "get_time": {"return": "uint64_t", "params": []},
        },
    }
    assert "<stdint.h>" in needed_standard_includes(data)


def test_std_includes_from_macro_value() -> None:
    data: dict = {
        "headers": {},
        "types": {},
        "macros": {"MY_MACRO": "(x) ((uint64_t)x)"},
        "enums": {},
        "structs": {},
        "functions": {},
    }
    assert "<stdint.h>" in needed_standard_includes(data)


def test_std_includes_rendered_in_types_header() -> None:
    data: dict = {
        "headers": {},
        "types": {"my_time": "uint64_t"},
        "macros": {},
        "enums": {},
        "structs": {},
        "functions": {},
    }
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        generate_defs_headers(str(out), data, verbose=False)
        content = (out / "include" / "mockware" / "types.h").read_text()
        assert "#include <stdint.h>" in content


def test_macro_normal_has_space() -> None:
    data: dict = {
        "headers": {},
        "types": {},
        "macros": {"ESP_OK": "0"},
        "enums": {},
        "structs": {},
        "functions": {},
    }
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        generate_defs_headers(str(out), data, verbose=False)
        content = (out / "include" / "mockware" / "macros.h").read_text()
        assert "#define ESP_OK 0" in content


def test_macro_function_like_no_space() -> None:
    data: dict = {
        "headers": {},
        "types": {},
        "macros": {"pdMS_TO_TICKS": "(x)"},
        "enums": {},
        "structs": {},
        "functions": {},
    }
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        generate_defs_headers(str(out), data, verbose=False)
        content = (out / "include" / "mockware" / "macros.h").read_text()
        assert "#define pdMS_TO_TICKS(x)" in content


def test_macro_function_like_with_value() -> None:
    data: dict = {
        "headers": {},
        "types": {},
        "macros": {"pdMS_TO_TICKS": "(x) * 1000"},
        "enums": {},
        "structs": {},
        "functions": {},
    }
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        generate_defs_headers(str(out), data, verbose=False)
        content = (out / "include" / "mockware" / "macros.h").read_text()
        assert "#define pdMS_TO_TICKS(x) * 1000" in content


def test_mixed_macros() -> None:
    data: dict = {
        "headers": {},
        "types": {},
        "macros": {
            "ESP_OK": "0",
            "pdMS_TO_TICKS": "(x)",
        },
        "enums": {},
        "structs": {},
        "functions": {},
    }
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        generate_defs_headers(str(out), data, verbose=False)
        content = (out / "include" / "mockware" / "macros.h").read_text()
        assert "#define ESP_OK 0" in content
        assert "#define pdMS_TO_TICKS(x)" in content
