import tempfile
from pathlib import Path

from mockware.generator.yaml_reader import read_yaml
from mockware.parser.yaml_writer import merge_into_yaml, write_yaml

SAMPLE_DATA: dict = {
    "headers": {
        "api/foo.h": {"includes": []},
        "api/baz.h": {"includes": ["api/foo.h"]},
    },
    "types": {"foo_t": "int", "baz_t": "float"},
    "macros": {"FOO": "1", "BAR": "2", "BAZ": "42"},
    "enums": {
        "baz_mode_t": {"values": {"BAZ_OFF": 0, "BAZ_ON": 1}},
    },
    "structs": {},
    "functions": {
        "do_foo": {"return": "void", "params": ["int x"],
                   "header": "api/foo.h"},
        "do_baz": {"return": "baz_t", "params": ["baz_mode_t mode"],
                   "header": "api/baz.h"},
    },
}


def test_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        yaml_path = Path(tmp) / "test.yml"
        write_yaml(SAMPLE_DATA, str(yaml_path))

        loaded = read_yaml(str(yaml_path))
        assert "api/foo.h" in loaded["headers"]
        assert loaded["types"]["foo_t"] == "int"
        assert loaded["macros"]["FOO"] == "1"
        assert loaded["enums"]["baz_mode_t"]["values"]["BAZ_OFF"] == 0
        assert loaded["functions"]["do_baz"]["return"] == "baz_t"
        assert loaded["functions"]["do_baz"]["header"] == "api/baz.h"


def test_yaml_has_blank_lines_between_sections() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        yaml_path = Path(tmp) / "test.yml"
        write_yaml(SAMPLE_DATA, str(yaml_path))
        content = yaml_path.read_text()
        section_keys = ["headers:", "types:", "macros:", "enums:", "structs:", "functions:"]
        for i, key in enumerate(section_keys):
            assert key in content, f"Missing section: {key}"
            idx = content.index(key)
            if i > 0:
                prev_line_end = content.rindex("\n", 0, idx)
                assert content[prev_line_end - 1] == "\n", \
                    f"No blank line before section: {key}"


def test_normalises_missing_sections() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        yaml_path = Path(tmp) / "partial.yml"
        yaml_path.write_text("headers: {}\n")

        loaded = read_yaml(str(yaml_path))
        assert loaded["headers"] == {}
        assert loaded["types"] == {}
        assert loaded["functions"] == {}


def test_merge_partial_adds_new_header() -> None:
    existing = {
        "headers": {
            "existing.h": {"includes": []},
        },
        "types": {},
        "macros": {"OLD": "0"},
        "enums": {},
        "structs": {},
        "functions": {},
    }
    scanned = {
        "headers": {
            "new.h": {"includes": []},
        },
        "types": {"new_t": "int"},
        "macros": {"NEW": "1"},
        "enums": {},
        "structs": {},
        "functions": {"new_func": {"return": "int", "params": []}},
    }
    merged = merge_into_yaml(existing, scanned, mode="partial")
    assert "existing.h" in merged["headers"]
    assert "new.h" in merged["headers"]
    assert merged["macros"]["OLD"] == "0"
    assert merged["macros"]["NEW"] == "1"
    assert merged["types"]["new_t"] == "int"
    assert merged["functions"]["new_func"] is not None


def test_merge_partial_does_not_overwrite() -> None:
    existing = {
        "headers": {},
        "types": {},
        "macros": {"EXISTING": "0"},
        "enums": {},
        "structs": {},
        "functions": {},
    }
    scanned = {
        "headers": {},
        "types": {},
        "macros": {"EXISTING": "99", "NEW": "1"},
        "enums": {},
        "structs": {},
        "functions": {},
    }
    merged = merge_into_yaml(existing, scanned, mode="partial")
    assert merged["macros"]["EXISTING"] == "0"
    assert merged["macros"]["NEW"] == "1"


def test_merge_full_overwrites() -> None:
    existing = {
        "headers": {},
        "types": {},
        "macros": {"OLD": "0"},
        "enums": {},
        "structs": {},
        "functions": {},
    }
    scanned = {
        "headers": {},
        "types": {},
        "macros": {"NEW": "1"},
        "enums": {},
        "structs": {},
        "functions": {},
    }
    merged = merge_into_yaml(existing, scanned, mode="full")
    assert merged["macros"] == {"NEW": "1"}
    assert "OLD" not in merged["macros"]


def test_merge_partial_merges_includes() -> None:
    existing = {
        "headers": {
            "h.h": {"includes": ["base.h"]},
        },
        "types": {},
        "macros": {},
        "enums": {},
        "structs": {},
        "functions": {},
    }
    scanned = {
        "headers": {
            "h.h": {"includes": ["extra.h", "base.h"]},
        },
        "types": {},
        "macros": {},
        "enums": {},
        "structs": {},
        "functions": {},
    }
    merged = merge_into_yaml(existing, scanned, mode="partial")
    assert merged["headers"]["h.h"]["includes"] == ["base.h", "extra.h"]
