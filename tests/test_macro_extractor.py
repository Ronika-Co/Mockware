import tempfile
from pathlib import Path

from mockware.parser.macro_extractor import _extract_via_regex


def test_object_like_macro() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp) / "test.h"
        h.write_text("#define FOO 42\n")
        macros = _extract_via_regex(h)
        assert macros["FOO"] == "42"


def test_multiple_object_macros() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp) / "test.h"
        h.write_text("#define FOO 42\n#define BAR \"hello\"\n")
        macros = _extract_via_regex(h)
        assert macros["FOO"] == "42"
        assert macros["BAR"] == '"hello"'


def test_function_like_macro() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp) / "test.h"
        h.write_text("#define MIN(a, b) ((a) < (b) ? (a) : (b))\n")
        macros = _extract_via_regex(h)
        entry = macros["MIN"]
        assert isinstance(entry, dict)
        assert entry["kind"] == "function-like"
        assert entry["params"] == ["a", "b"]
        assert "((a) < (b) ? (a) : (b))" in entry["body"]


def test_variadic_function_like_macro() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp) / "test.h"
        h.write_text("#define PRINT(fmt, ...) printf(fmt, ##__VA_ARGS__)\n")
        macros = _extract_via_regex(h)
        entry = macros["PRINT"]
        assert isinstance(entry, dict)
        assert entry["kind"] == "function-like"
        assert entry["variadic"] is True


def test_mixed_macros() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp) / "test.h"
        h.write_text(
            "#define MAX(a, b) ((a) > (b) ? (a) : (b))\n#define PI 3.14\n"
        )
        macros = _extract_via_regex(h)
        assert isinstance(macros["MAX"], dict)
        assert macros["PI"] == "3.14"


def test_empty_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp) / "empty.h"
        h.write_text("// just a comment\n")
        macros = _extract_via_regex(h)
        assert macros == {}
