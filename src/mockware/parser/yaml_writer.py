from __future__ import annotations

from copy import deepcopy

import yaml


def write_yaml(data: dict, output_path: str) -> None:
    """Write the 6-section YAML format with blank lines between sections.

    Expected top-level keys: ``headers``, ``types``, ``macros``,
    ``enums``, ``structs``, ``functions``.
    """
    payload = _format_for_yaml(data)

    class _LiteralStr(str):
        pass

    def _represent_literal(dumper: yaml.Dumper, data: _LiteralStr) -> object:
        return dumper.represent_scalar("tag:yaml.org,2002:str",
                                       str(data), style="|")

    yaml.add_representer(_LiteralStr, _represent_literal)

    for sname, sinfo in payload.get("structs", {}).items():
        if isinstance(sinfo, str):
            sinfo = payload["structs"][sname] = {"definition": sinfo}
        if "definition" in sinfo:
            sinfo["definition"] = _LiteralStr(sinfo["definition"])

    sections_order = ["headers", "types", "macros", "enums", "structs",
                      "functions"]
    yaml_parts: list[str] = []
    for key in sections_order:
        section = payload.get(key, {})
        part = yaml.dump({key: section}, default_flow_style=False,
                         sort_keys=False, allow_unicode=True)
        yaml_parts.append(part)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(yaml_parts))


def _format_for_yaml(data: dict) -> dict:
    """Ensure every section is a dict with sorted keys."""
    result: dict = {}
    for key in ("headers", "types", "macros", "enums", "structs", "functions"):
        section = data.get(key, {}) if key != "structs" else data.get(key, {})
        if not section:
            section = {}
        result[key] = dict(sorted(section.items())) if isinstance(section, dict) else section
    return result


def merge_into_yaml(
    existing: dict,
    scanned: dict,
    mode: str = "partial",
) -> dict:
    """Merge *scanned* data into *existing*, preserving existing keys.

    In *full* mode returns a deep copy of *scanned*.
    In *partial* mode merges each section independently:
      - headers: per-header merge (new headers added, existing preserved)
      - types/macros/enums/structs: union, existing keys win
      - functions: union, existing keys win
    """
    if mode == "full":
        return deepcopy(scanned)

    result = deepcopy(existing)

    # Merge headers (per-key, preserving existing)
    for hdr_key, scanned_entry in scanned.get("headers", {}).items():
        if hdr_key not in result.get("headers", {}):
            result.setdefault("headers", {})[hdr_key] = deepcopy(scanned_entry)
        else:
            existing_entry = result["headers"][hdr_key]
            for inc in scanned_entry.get("includes", []):
                if inc not in existing_entry.get("includes", []):
                    existing_entry.setdefault("includes", []).append(inc)

    # Dict-based sections: union, existing keys win
    for section in ("types", "macros", "enums", "structs", "functions"):
        scanned_sec = scanned.get(section, {})
        existing_sec = result.get(section, {})
        for k, v in scanned_sec.items():
            if k not in existing_sec:
                existing_sec[k] = deepcopy(v)
        result[section] = existing_sec

    return result
