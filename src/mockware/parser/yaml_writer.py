from __future__ import annotations

import yaml


def write_yaml(data: dict[str, dict], output_path: str) -> None:
    """Write the parsed ESP-IDF API data to a YAML file.

    The top-level key is ``headers``, mapping header include paths to
    their includes, macros, types, enums, structs, and functions.
    """
    # Move component-grouped keys under a top-level "headers" key
    payload: dict = {"headers": {}}

    for hdr_key, entry in sorted(data.items()):
        payload["headers"][hdr_key] = entry

    class _LiteralStr(str):
        pass

    def _represent_literal(dumper: yaml.Dumper, data: _LiteralStr) -> object:
        return dumper.represent_scalar("tag:yaml.org,2002:str",
                                       str(data), style="|")

    yaml.add_representer(_LiteralStr, _represent_literal)

    # Mark definition fields as literal blocks
    for hdr_key, entry in data.items():
        for sname, sinfo in entry.get("structs", {}).items():
            if "definition" in sinfo:
                sinfo["definition"] = _LiteralStr(sinfo["definition"])

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(payload, f, default_flow_style=False,
                  sort_keys=False, allow_unicode=True)
