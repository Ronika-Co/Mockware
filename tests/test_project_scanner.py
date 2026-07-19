import tempfile
from pathlib import Path

import yaml

from mockware.generator.project_scanner import find_used_headers


def _write_yaml(path: Path, headers: list[str]) -> None:
    data = {"headers": {}}
    for h in headers:
        data["headers"][h] = {"includes": []}
    path.write_text(yaml.dump(data))


def test_finds_simple_include() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        main_c = Path(tmp) / "main.c"
        main_c.write_text('#include "driver/gpio.h"\n')
        yml = Path(tmp) / "apis.yml"
        _write_yaml(yml, ["driver/gpio.h"])
        used = find_used_headers(tmp, str(yml), verbose=False)
        assert used == {"driver/gpio.h"}


def test_finds_multiple_includes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "app.c"
        src.write_text(
            '#include "foo.h"\n#include "bar.h"\n#include "baz.h"\n'
        )
        yml = Path(tmp) / "apis.yml"
        _write_yaml(yml, ["foo.h", "bar.h", "baz.h"])
        used = find_used_headers(tmp, str(yml), verbose=False)
        assert used == {"foo.h", "bar.h", "baz.h"}


def test_finds_includes_across_multiple_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "a.c").write_text('#include "alpha.h"\n')
        (Path(tmp) / "b.c").write_text('#include "beta.h"\n')
        yml = Path(tmp) / "apis.yml"
        _write_yaml(yml, ["alpha.h", "beta.h"])
        used = find_used_headers(tmp, str(yml), verbose=False)
        assert used == {"alpha.h", "beta.h"}


def test_scans_subdirectories() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        sub = Path(tmp) / "sub" / "nested"
        sub.mkdir(parents=True)
        (sub / "code.c").write_text('#include "mylib/core.h"\n')
        yml = Path(tmp) / "apis.yml"
        _write_yaml(yml, ["mylib/core.h"])
        used = find_used_headers(tmp, str(yml), verbose=False)
        assert used == {"mylib/core.h"}


def test_ignores_includes_not_in_yaml() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "main.c").write_text(
            '#include <stdio.h>\n#include "my_local.h"\n'
        )
        yml = Path(tmp) / "apis.yml"
        _write_yaml(yml, [])
        used = find_used_headers(tmp, str(yml), verbose=False)
        assert used == set()


def test_handles_empty_directories() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        yml = Path(tmp) / "apis.yml"
        _write_yaml(yml, ["some/header.h"])
        used = find_used_headers(tmp, str(yml), verbose=False)
        assert used == set()
