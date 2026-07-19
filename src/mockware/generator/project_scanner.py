from __future__ import annotations

import os
import re
from pathlib import Path

import click

_INCLUDE_RE = re.compile(
    r'#include\s+[<"]'
    r'([^>"]+)'
    r'[>"]'
)


def find_used_headers(
    project_path: str,
    yaml_path: str,
    verbose: bool,
) -> set[str]:
    """Recursively scan *project_path* for #include directives.

    Returns a set of header paths that were found in the project's source
    files AND exist in the YAML ``headers`` section.
    """
    from .yaml_reader import read_yaml

    data = read_yaml(yaml_path)
    known_keys = set(data.get("headers", {}).keys())

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

            for match in _INCLUDE_RE.finditer(text):
                include_path = match.group(1)
                if include_path in known_keys:
                    used.add(include_path)

            if verbose:
                click.echo(f"    scanned {fname}")

    return used
