from __future__ import annotations

import re
from pathlib import Path

import click

_INCLUDE_RE = re.compile(
    r'#include\s+([<"])'
    r'([^>"]+)'
    r'[>"]'
)

_STDLIB_HEADERS = frozenset({
    "assert.h", "complex.h", "ctype.h", "errno.h", "fenv.h",
    "float.h", "inttypes.h", "iso646.h", "limits.h", "locale.h",
    "math.h", "setjmp.h", "signal.h", "stdalign.h", "stdarg.h",
    "stdatomic.h", "stdbit.h", "stdbool.h", "stdckdint.h", "stddef.h",
    "stdint.h", "stdio.h", "stdlib.h", "stdnoreturn.h", "string.h",
    "tgmath.h", "threads.h", "time.h", "uchar.h", "wchar.h",
    "wctype.h",
})

# Patterns to detect project-internal type/function definitions
_TYPEDEF_COMPOUND_RE = re.compile(
    r'typedef\s+(?:struct\s+\w+\s*)?\{[^}]*\}\s*(\w+)\s*;'
)
_TYPEDEF_SIMPLE_RE = re.compile(
    r'typedef\s+'
    r'(?:const\s+|volatile\s+)?'
    r'(?:\w+(?:\s+(?:const\s+)?)+)'  # base type (one or more words)
    r'(\w+)\s*;'
)
_ENUM_DEF_RE = re.compile(r'typedef\s+enum\s*\{[^}]*\}\s*(\w+)\s*;')
_STRUCT_DEF_RE = re.compile(r'struct\s+(\w+)\s*\{')
_FUNC_DECL_RE = re.compile(
    r'(?:^|\n|;|\{)\s*'
    r'(?:static\s+|extern\s+)?'
    r'(\w[\w\s*]*)\s+'             # return type
    r'(\w+)\s*\([^)]*\)\s*;'       # function name
)


def find_missing_deps(
    source_path: str,
    extra_includes: list[str] | None = None,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    verbose: bool = False,
) -> dict[str, dict]:
    """Scan *source_path* for #include directives to non-existent headers.

    Returns ``{header_path: {"includes": []}}`` — a dict of missing
    external headers with an empty include list (transitive deps of the
    missing headers cannot be known and must be supplied by the user).
    """
    if include_patterns is None:
        include_patterns = ["**/*.c", "**/*.h", "**/*.cpp", "**/*.hpp",
                            "**/*.cc", "**/*.cxx"]
    if exclude_patterns is None:
        exclude_patterns = []

    check_dirs = _resolve_include_dirs(source_path, extra_includes or [])
    src_files = _collect_source_files(source_path, include_patterns,
                                      exclude_patterns)
    if not src_files:
        click.echo("No source files found matching patterns")
        return {}

    # Collect all includes + track which files they came from (for
    # relative-path resolution of quoted includes)
    file_includes: dict[str, list[tuple[str, bool]]] = {}
    for fpath in src_files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        includes: list[tuple[str, bool]] = []
        for match in _INCLUDE_RE.finditer(text):
            delim = match.group(1)
            inc_path = match.group(2)
            is_quote = delim == '"'
            includes.append((inc_path, is_quote))
        if includes:
            file_includes[str(fpath)] = includes

    missing: set[str] = set()
    seen: set[str] = set()

    for fpath, includes in file_includes.items():
        src_dir = str(Path(fpath).parent)
        for inc_path, is_quote in includes:
            if inc_path in seen:
                continue
            seen.add(inc_path)
            if not is_quote and inc_path in _STDLIB_HEADERS:
                continue
            if _header_exists(inc_path, source_path, src_dir,
                              check_dirs, is_quote):
                continue
            missing.add(inc_path)

    if verbose:
        click.echo(f"  total unique non-stdlib includes: "
                   f"{len(seen - _STDLIB_HEADERS)}")
        click.echo(f"  found in project:      "
                   f"{len(seen - missing - _STDLIB_HEADERS)}")
        click.echo(f"  missing (external):    {len(missing)}")
        for h in sorted(missing):
            click.echo(f"    missing: {h}")

    return {hdr: {"includes": []} for hdr in missing}


def scan_project_symbols(
    source_path: str,
    exclude_patterns: list[str] | None = None,
) -> dict[str, set[str]]:
    """Scan project headers for types & functions defined internally.

    Returns ``{"types": {...}, "functions": {...}}``.  The caller uses
    this to filter out project-internal symbols from inference results.
    """
    from fnmatch import fnmatch

    if exclude_patterns is None:
        exclude_patterns = []
    result: dict[str, set[str]] = {"types": set(), "functions": set()}
    src = Path(source_path)

    for fpath in sorted(src.rglob("*.h")):
        rel = str(fpath.relative_to(src))
        if any(fnmatch(rel, pat) for pat in exclude_patterns):
            continue
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for m in _TYPEDEF_COMPOUND_RE.finditer(text):
            result["types"].add(m.group(1))
        for m in _TYPEDEF_SIMPLE_RE.finditer(text):
            result["types"].add(m.group(1))
        for m in _ENUM_DEF_RE.finditer(text):
            result["types"].add(m.group(1))
        for m in _STRUCT_DEF_RE.finditer(text):
            result["types"].add(f"struct {m.group(1)}")
        for m in _FUNC_DECL_RE.finditer(text):
            result["functions"].add(m.group(2))

    return result


def _resolve_include_dirs(source_path: str, extra: list[str]) -> list[str]:
    dirs = list(extra)
    src = Path(source_path).resolve()
    dirs.append(str(src))
    return dirs


def _collect_source_files(
    source_path: str,
    include_patterns: list[str],
    exclude_patterns: list[str],
) -> list[Path]:
    from fnmatch import fnmatch

    def _is_excluded(rel: str) -> bool:
        return any(fnmatch(rel, pat) for pat in exclude_patterns)

    src = Path(source_path)
    files: list[Path] = []
    for pattern in include_patterns:
        for fpath in sorted(src.rglob(pattern)):
            if not fpath.is_file():
                continue
            rel = str(fpath.relative_to(src))
            if _is_excluded(rel):
                continue
            files.append(fpath)
    return files


def _header_exists(
    include_path: str,
    source_path: str,
    source_dir: str,
    check_dirs: list[str],
    is_quote: bool,
) -> bool:
    if is_quote:
        candidate = Path(source_dir) / include_path
        if candidate.exists():
            return True
    candidate = Path(source_path) / include_path
    if candidate.exists():
        return True
    for d in check_dirs:
        candidate = Path(d) / include_path
        if candidate.exists():
            return True
    return False
