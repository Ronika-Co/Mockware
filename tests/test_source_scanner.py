import tempfile
from pathlib import Path

from mockware.parser.source_scanner import (
    find_missing_deps,
    scan_project_symbols,
)


def test_include_that_exists_in_project_is_not_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "main.c").write_text('#include "my_header.h"\n')
        (Path(tmp) / "my_header.h").write_text("int x;\n")
        missing = find_missing_deps(tmp, verbose=False)
        assert missing == {}


def test_include_that_does_not_exist_is_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "main.c").write_text('#include "external.h"\n')
        missing = find_missing_deps(tmp, verbose=False)
        assert "external.h" in missing


def test_multiple_missing_includes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "app.c").write_text(
            '#include "lib_a.h"\n#include "lib_b.h"\n'
        )
        missing = find_missing_deps(tmp, verbose=False)
        assert "lib_a.h" in missing
        assert "lib_b.h" in missing


def test_mixed_present_and_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "test.c").write_text(
            '#include "present.h"\n#include "missing.h"\n'
        )
        (Path(tmp) / "present.h").write_text("int x;\n")
        missing = find_missing_deps(tmp, verbose=False)
        assert "present.h" not in missing
        assert "missing.h" in missing


def test_missing_header_in_include_dir_resolves() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        inc = Path(tmp) / "include"
        inc.mkdir()
        (inc / "sdk.h").write_text("int x;\n")
        (Path(tmp) / "main.c").write_text('#include "sdk.h"\n')
        missing = find_missing_deps(tmp, extra_includes=[str(inc)],
                                   verbose=False)
        assert missing == {}


def test_scans_subdirectories() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        sub = Path(tmp) / "src"
        sub.mkdir()
        (sub / "main.c").write_text('#include "ext.h"\n')
        missing = find_missing_deps(tmp, verbose=False)
        assert "ext.h" in missing


def test_handles_bracket_includes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "main.c").write_text('#include <system_lib.h>\n')
        missing = find_missing_deps(tmp, verbose=False)
        assert "system_lib.h" in missing


def test_handles_empty_project() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        missing = find_missing_deps(tmp, verbose=False)
        assert missing == {}


def test_system_header_not_missing_if_in_include_dir() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        inc = Path(tmp) / "sys"
        inc.mkdir()
        (inc / "cstdlib.h").write_text("int x;\n")
        (Path(tmp) / "main.c").write_text('#include <cstdlib.h>\n')
        missing = find_missing_deps(tmp, extra_includes=[str(inc)],
                                   verbose=False)
        assert missing == {}


def test_scan_project_symbols_excludes_patterns() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "sdk_types.h").write_text(
            'typedef int my_sdk_type_t;\n'
        )
        inc = Path(tmp) / "mock-sdk" / "include"
        inc.mkdir(parents=True)
        (inc / "types.h").write_text(
            'typedef int sdk_type_t;\n'
        )
        syms = scan_project_symbols(tmp, exclude_patterns=["mock-sdk/**"])
        assert "my_sdk_type_t" in syms["types"]
        assert "sdk_type_t" not in syms["types"]
