from __future__ import annotations

import re
import subprocess
from pathlib import Path

import click


def extract_macros(
    idf_path: str,
    headers: dict[str, list[str]],
    existing: dict[str, dict],
    extra_includes: list[str],
    verbose: bool,
) -> dict[str, dict]:
    """Extract #define macros from each header and merge into existing data.

    Uses two strategies:
      1. ``gcc -E -dM`` dumps all defines after preprocessing (includes
         transitive macros — filtered to only keep those defined in the
         original header).
      2.  Fallback regex scan on the raw header text for simple cases.
    """
    comp_dir = Path(idf_path) / "components"

    for comp_name, rels in headers.items():
        for rel in rels:
            hdr_path = comp_dir / comp_name / "include" / rel
            hdr_key = _header_key(comp_name, rel)
            if hdr_key not in existing:
                existing[hdr_key] = _empty_entry()

            macros = _extract_via_dm(hdr_path, idf_path, extra_includes)
            if macros is None:
                macros = _extract_via_regex(hdr_path)

            existing[hdr_key]["macros"].update(macros)
            if verbose and macros:
                click.echo(f"  macros in {rel}: {len(macros)}")

    return existing


def _header_key(comp_name: str, rel: str) -> str:
    """Return the key string used in the YAML (e.g. ``freertos/FreeRTOS.h``).

    If the component name is the first directory in the relative path, we
    simply use the relative path; otherwise we prepend the component.
    """
    if rel.startswith(comp_name):
        return rel
    return f"{comp_name}/{rel}"


def _empty_entry() -> dict:
    return {"includes": [], "macros": {}, "types": {},
            "enums": {}, "structs": {}, "functions": {}}


# ── -dM approach ────────────────────────────────────────────────────────


def _extract_via_dm(
    hdr_path: Path,
    idf_path: str,
    extra_includes: list[str],
) -> dict[str, str | dict] | None:
    """Run ``gcc -E -dM`` and return macros defined in *hdr_path*."""
    try:
        cmd = ["gcc", "-E", "-dM", "-x", "c"]
        for inc in _all_include_dirs(idf_path, extra_includes):
            cmd.extend(["-I", inc])
        cmd.append(str(hdr_path))

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None

        macros: dict[str, str | dict] = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line.startswith("#define "):
                continue
            parts = line.split(None, 2)
            if len(parts) < 2:
                continue
            name = parts[1]
            value = parts[2] if len(parts) > 2 else ""

            macros[name] = value

        return macros
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


# ── Regex fallback ──────────────────────────────────────────────────────


_OBJECT_MACRO_RE = re.compile(r'#define\s+(\w+)\s+(.*)')
_FUNC_MACRO_RE = re.compile(
    r'#define\s+(\w+)\(([^)]*)\)\s+(.*?)(?:\s*/\*.*?\*/\s*)?$',
    re.MULTILINE | re.DOTALL,
)


def _extract_via_regex(hdr_path: Path) -> dict[str, str | dict]:
    """Extract macros from raw header text (simple regex)."""
    text = hdr_path.read_text(encoding="utf-8", errors="replace")

    macros: dict[str, str | dict] = {}

    # function-like macros
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
            "body": body,
        }

    # object-like macros
    for match in _OBJECT_MACRO_RE.finditer(text):
        name = match.group(1)
        if name in macros:
            continue
        value = match.group(2).strip().rstrip("\\")
        macros[name] = value

    return macros


# ── Shared helpers ──────────────────────────────────────────────────────


def _all_include_dirs(idf_path: str, extra: list[str]) -> list[str]:
    dirs = list(extra)
    comp_dir = Path(idf_path) / "components"
    if comp_dir.is_dir():
        for child in sorted(comp_dir.iterdir()):
            inc = child / "include"
            if inc.is_dir():
                dirs.append(str(inc))
    return dirs
