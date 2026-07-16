from __future__ import annotations

import os
from pathlib import Path

import click


def discover_headers(
    idf_path: str,
    components_filter: str | None = None,
    verbose: bool = False,
) -> dict[str, list[str]]:
    """Walk IDF_PATH/components/*/include/ and return {component: [rel_path, ...]}.

    ``rel_path`` is the path relative to the component's include directory,
    preserving subdirectory structure (e.g. ``freertos/FreeRTOS.h``).
    """
    components_dir = Path(idf_path) / "components"
    if not components_dir.is_dir():
        raise FileNotFoundError(f"{components_dir} does not exist")

    allowed = set()
    if components_filter:
        allowed = {c.strip() for c in components_filter.split(",")}

    result: dict[str, list[str]] = {}

    for comp_dir in sorted(components_dir.iterdir()):
        if not comp_dir.is_dir():
            continue
        comp_name = comp_dir.name
        if allowed and comp_name not in allowed:
            continue

        include_dir = comp_dir / "include"
        if not include_dir.is_dir():
            continue

        rels: list[str] = []
        for root, _dirs, files in os.walk(include_dir):
            for f in sorted(files):
                if not f.endswith(".h"):
                    continue
                full = Path(root) / f
                rel = str(full.relative_to(include_dir))
                rels.append(rel)

        if rels:
            result[comp_name] = rels
            if verbose:
                click.echo(f"  {comp_name}: {len(rels)} header(s)")

    return result

