from __future__ import annotations

from pathlib import Path

import yaml


def read_yaml(yaml_path: str) -> dict:
    """Read the 6-section YAML format.

    Returns a dict with keys: ``headers``, ``types``, ``macros``,
    ``enums``, ``structs``, ``functions``.
    """
    raw = yaml.safe_load(Path(yaml_path).read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise ValueError(f"YAML root must be a dict, got {type(raw).__name__}")

    return _normalise(raw)


def _normalise(raw: dict) -> dict:
    """Fill missing sections with empty defaults."""
    result: dict = {}

    for key in ("headers", "types", "macros", "enums", "structs", "functions"):
        section = raw.get(key, {})
        if not isinstance(section, dict):
            section = {}
        result[key] = section

    # Normalise each header entry
    headers: dict[str, dict] = {}
    for hdr_key, entry in result.get("headers", {}).items():
        if entry is None:
            entry = {}
        headers[hdr_key] = {
            "includes": entry.get("includes", []),
        }
    result["headers"] = headers

    return result
