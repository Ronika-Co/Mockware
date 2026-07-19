import tempfile
from pathlib import Path

from mockware.parser.header_parser import (
    _extract_function_calls,
    _extract_macro_candidates,
    _extract_type_refs,
    _strip_comments,
    infer_missing_apis,
)


def test_strip_comments_removes_block_comments() -> None:
    text = "int a; /* block comment */ int b;"
    assert _strip_comments(text) == "int a;  int b;"


def test_strip_comments_removes_line_comments() -> None:
    text = "int a; // line comment\nint b;"
    assert _strip_comments(text) == "int a; \nint b;"


def test_extract_function_calls_simple() -> None:
    text = "void test() { foo(1, 2); bar(); }"
    calls = _extract_function_calls(text)
    assert any(name == "foo" for name, _, _ in calls)
    assert any(name == "bar" for name, _, _ in calls)


def test_extract_function_calls_skips_keywords() -> None:
    text = "if (x) { while (1) { break; } }"
    calls = _extract_function_calls(text)
    assert not any(name in ("if", "while", "break") for name, _, _ in calls)


def test_extract_function_calls_nested_parens() -> None:
    text = "foo(1, bar(2, 3), 4);"
    calls = _extract_function_calls(text)
    assert any(name == "foo" for name, argc, _ in calls)
    foo = next((argc for name, argc, _ in calls if name == "foo"), 0)
    assert foo == 3


def test_extract_function_calls_no_args() -> None:
    text = "void test() { baz(); }"
    calls = _extract_function_calls(text)
    baz = next((argc for name, argc, _ in calls if name == "baz"), -1)
    assert baz == 0


def test_extract_type_refs_in_declarations() -> None:
    text = "my_type_t var;"
    types = _extract_type_refs(text, set())
    assert "my_type_t" in types


def test_extract_type_refs_in_casts() -> None:
    text = "(my_type_t*)ptr;"
    types = _extract_type_refs(text, set())
    assert "my_type_t" in types


def test_extract_type_refs_skips_builtins() -> None:
    text = "int x; float y;"
    types = _extract_type_refs(text, set())
    assert "int" not in types
    assert "float" not in types


def test_extract_type_refs_skips_project_types() -> None:
    text = "my_type_t var;"
    types = _extract_type_refs(text, {"my_type_t"})
    assert "my_type_t" not in types


def test_extract_macro_candidates() -> None:
    text = "if (ret != ESP_OK) { return ESP_FAIL; }"
    macros = _extract_macro_candidates(text)
    assert "ESP_OK" in macros
    assert "ESP_FAIL" in macros


def test_extract_macro_candidates_function_like() -> None:
    """Function-like macros (ALL_CAPS followed by `(`) are included."""
    text = "vTaskDelay(pdMS_TO_TICKS(100));"
    macros = _extract_macro_candidates(text)
    assert "pdMS_TO_TICKS" in macros


def test_infer_missing_apis_detects_functions() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp)
        (src / "main.c").write_text(
            '#include "external.h"\n'
            'void test() {\n'
            '    external_init(42);\n'
            '    external_start();\n'
            '}\n'
        )
        missing = {"external.h": {"includes": []}}
        result = infer_missing_apis(str(src), missing, verbose=False)
        assert "external.h" in result["headers"]
        funcs = result["functions"]
        assert "external_init" in funcs
        assert "external_start" in funcs
        assert funcs["external_init"]["header"] == "external.h"
        assert len(funcs["external_init"]["params"]) == 1
        assert len(funcs["external_start"]["params"]) == 0


def test_infer_missing_apis_detects_types() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp)
        (src / "main.c").write_text(
            '#include "sdk.h"\n'
            'void test() {\n'
            '    sdk_status_t ret = sdk_init();\n'
            '}\n'
        )
        missing = {"sdk.h": {"includes": []}}
        result = infer_missing_apis(str(src), missing, verbose=False)
        assert "sdk_status_t" in result["types"]
        assert result["types"]["sdk_status_t"] == "int"


def test_infer_missing_apis_global_types() -> None:
    """Types are global, not per-header."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp)
        (src / "app.c").write_text(
            '#include "lib_a.h"\n'
            '#include "lib_b.h"\n'
            'void test() {\n'
            '    result_t r;\n'
            '}\n'
        )
        missing = {"lib_a.h": {"includes": []}, "lib_b.h": {"includes": []}}
        result = infer_missing_apis(str(src), missing, verbose=False)
        # result_t appears once in global types, not duplicated
        assert "result_t" in result["types"]


def test_project_enum_excluded_from_yaml() -> None:
    """Enums defined in project headers are excluded from the output."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp)
        (src / "project.h").write_text(
            'typedef enum { FOO_OK = 0, FOO_FAIL = -1 } project_status_t;\n'
        )
        (src / "main.c").write_text(
            '#include "project.h"\n'
            '#include "sdk.h"\n'
            'void test() {\n'
            '    project_status_t s = sdk_init();\n'
            '    if (s != FOO_OK) return;\n'
            '}\n'
        )
        missing = {"sdk.h": {"includes": []}}
        result = infer_missing_apis(str(src), missing, verbose=False)
        # project_status_t is defined in project header — excluded from enums
        assert "project_status_t" not in result["enums"]
        # FOO_OK/FOO_FAIL are project enum values — excluded from macros
        assert "FOO_OK" not in result["macros"]
        assert "FOO_FAIL" not in result["macros"]
        # sdk_init is from external SDK — should appear in functions
        assert "sdk_init" in result["functions"]


def test_project_struct_excluded_from_yaml() -> None:
    """Structs defined in project headers are excluded from the output."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp)
        (src / "project.h").write_text(
            'struct config { int x; int y; };\n'
        )
        (src / "main.c").write_text(
            '#include "project.h"\n'
            '#include "sdk.h"\n'
            'void test() {\n'
            '    struct config cfg;\n'
            '    sdk_configure(&cfg);\n'
            '}\n'
        )
        missing = {"sdk.h": {"includes": []}}
        result = infer_missing_apis(str(src), missing, verbose=False)
        # config is defined in project header — excluded from structs
        assert "config" not in result["structs"]


def test_external_enum_appears_in_yaml() -> None:
    """Enums used from external SDK headers appear in the output."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp)
        (src / "main.c").write_text(
            '#include "sdk.h"\n'
            'typedef enum { SDK_MODE_A = 0, SDK_MODE_B = 1 } sdk_mode_t;\n'
            'void test() {\n'
            '    sdk_mode_t m = SDK_MODE_A;\n'
            '}\n'
        )
        missing = {"sdk.h": {"includes": []}}
        result = infer_missing_apis(str(src), missing, verbose=False)
        # sdk_mode_t is not defined in a project header — appears in enums
        assert "sdk_mode_t" in result["enums"]
        assert result["enums"]["sdk_mode_t"]["values"]["SDK_MODE_A"] == 0
        assert result["enums"]["sdk_mode_t"]["values"]["SDK_MODE_B"] == 1


def test_enum_values_still_excluded_from_macros() -> None:
    """Enum values from project-internal enums don't leak into macros."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp)
        (src / "project.h").write_text(
            'typedef enum { MY_OK = 0, MY_FAIL = -1 } my_status_t;\n'
        )
        (src / "main.c").write_text(
            '#include "project.h"\n'
            '#include "sdk.h"\n'
            'void test() {\n'
            '    if (sdk_call() != MY_OK)\n'
            '        return MY_FAIL;\n'
            '}\n'
        )
        missing = {"sdk.h": {"includes": []}}
        result = infer_missing_apis(str(src), missing, verbose=False)
        # Project enum is excluded
        assert "my_status_t" not in result["enums"]
        # Enum values still excluded from macros
        assert "MY_OK" not in result["macros"]
        assert "MY_FAIL" not in result["macros"]


def test_exclude_patterns_prevents_generated_sdk_scan() -> None:
    """Exclude patterns are passed to scan_project_symbols, preventing
    generated mock-sdk types from being treated as project-internal."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp)

        # Project file using an external SDK type
        (src / "main.c").write_text(
            '#include "esp_wifi.h"\n'
            'void test() {\n'
            '    esp_err_t ret = esp_wifi_start();\n'
            '}\n'
        )

        # Generated mock-sdk (would pollute project_types if scanned)
        gen = src / "mock-sdk" / "include" / "mockware"
        gen.mkdir(parents=True)
        (gen / "types.h").write_text('typedef int esp_err_t;\n')

        missing = {"esp_wifi.h": {"includes": []}}
        result = infer_missing_apis(
            str(src), missing,
            exclude_patterns=["mock-sdk/**"],
            verbose=False,
        )
        # esp_err_t should appear in types (not filtered as project-internal)
        assert "esp_err_t" in result["types"]
