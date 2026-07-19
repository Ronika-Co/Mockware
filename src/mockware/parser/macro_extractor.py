from __future__ import annotations

import re
from pathlib import Path


def extract_macros(
    source_path: str,
    headers: dict[str, list[str]],
    existing: dict[str, dict],
    extra_includes: list[str] | None = None,
    defines: list[str] | None = None,
    verbose: bool = False,
) -> dict[str, dict]:
    """No-op: macros from external headers cannot be inferred from usage.

    Macros must be added manually to the YAML file by the user.
    This function exists as a stub for the CLI pipeline.
    """
    return existing


# ── Regex-based macro extraction (kept as utility) ───────────────────


_COMMENT_RE = re.compile(r'/\*.*?\*/', re.DOTALL)


def _strip_comment(text: str) -> str:
    return _COMMENT_RE.sub('', text).strip()


_OBJECT_MACRO_RE = re.compile(r'#define\s+(\w+)\s+(.*)')
_FUNC_MACRO_RE = re.compile(
    r'#define\s+(\w+)\(([^)]*)\)\s+(.*?)(?:\s*/\*.*?\*/\s*)?$',
    re.MULTILINE | re.DOTALL,
)


def _extract_via_regex(hdr_path: Path) -> dict[str, str | dict]:
    """Extract macros from raw header text using regex.

    Useful for scanning headers that *do* exist locally.
    """
    text = hdr_path.read_text(encoding="utf-8", errors="replace")

    macros: dict[str, str | dict] = {}

    for match in _FUNC_MACRO_RE.finditer(text):
        name = match.group(1)
        params_str = match.group(2).strip()
        body = match.group(3).strip().rstrip("\\")

        params = [p.strip() for p in params_str.split(",") if p.strip()]
        is_variadic = "..." in params_str

        macros[name] = {
            "kind": "function-like",
            "params": params,
            "variadic": is_variadic,
            "body": _strip_comment(body),
        }

    for match in _OBJECT_MACRO_RE.finditer(text):
        name = match.group(1)
        if name in macros:
            continue
        value = match.group(2).strip().rstrip("\\")
        macros[name] = _strip_comment(value)

    return macros
