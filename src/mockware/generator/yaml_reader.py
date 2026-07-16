from __future__ import annotations

from pathlib import Path

import yaml


def read_yaml(yaml_path: str) -> dict[str, dict]:
    """Read the YAML knowledge base and return {header_path: data}.

    The expected top-level key is ``headers``.
    """
    raw = yaml.safe_load(Path(yaml_path).read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise ValueError(f"YAML root must be a dict, got {type(raw).__name__}")

    headers = raw.get("headers")
    if headers is None:
        raise ValueError("YAML is missing top-level 'headers' key")

    # Ensure all entries have the expected structure
    result: dict[str, dict] = {}
    for hdr_key, entry in headers.items():
        result[hdr_key] = _normalise(entry)

    return result


def _normalise(entry: dict | None) -> dict:
    if entry is None:
        entry = {}
    return {
        "includes": entry.get("includes", []),
        "macros": entry.get("macros", {}),
        "types": entry.get("types", {}),
        "enums": entry.get("enums", {}),
        "structs": entry.get("structs", {}),
        "functions": entry.get("functions", {}),
    }
