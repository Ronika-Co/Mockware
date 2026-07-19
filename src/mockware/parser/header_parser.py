from __future__ import annotations

import re
from pathlib import Path

import click

_C_KEYWORDS = {
    "if", "while", "for", "switch", "case", "return", "sizeof",
    "int", "void", "char", "float", "double", "long", "short",
    "unsigned", "signed", "const", "static", "extern", "volatile",
    "struct", "union", "enum", "typedef", "auto", "register",
    "goto", "break", "continue", "default", "do", "else",
    "_Bool", "_Complex", "_Imaginary", "inline", "restrict",
}

_C_BUILTIN_TYPES = {
    "int", "void", "char", "float", "double", "long", "short",
    "return", "typedef", "unsigned", "signed", "size_t", "ssize_t", "ptrdiff_t",
    "int8_t", "int16_t", "int32_t", "int64_t",
    "uint8_t", "uint16_t", "uint32_t", "uint64_t",
    "uintptr_t", "intptr_t", "wchar_t", "bool", "_Bool",
    "FILE", "va_list", "off_t", "time_t", "clock_t",
    "int_least8_t", "int_least16_t", "int_least32_t", "int_least64_t",
    "uint_least8_t", "uint_least16_t", "uint_least32_t", "uint_least64_t",
    "int_fast8_t", "int_fast16_t", "int_fast32_t", "int_fast64_t",
    "uint_fast8_t", "uint_fast16_t", "uint_fast32_t", "uint_fast64_t",
    "intmax_t", "uintmax_t", "float32_t", "float64_t",
}


def infer_missing_apis(
    source_path: str,
    missing_headers: dict[str, dict],
    source_file: str | None = None,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    verbose: bool = False,
) -> dict:
    """Infer function signatures, types, macros, enums and structs.

    Analysis is global — extracted symbols are not assigned to individual
    headers.  Functions are tagged with a ``header`` field when naming
    convention provides a plausible match; otherwise they go to
    ``general.c``.

    Returns a dict with keys:
      headers, types, macros, enums, structs, functions
    """
    from .source_scanner import scan_project_symbols

    if include_patterns is None:
        include_patterns = ["**/*.c", "**/*.h", "**/*.cpp", "**/*.hpp",
                            "**/*.cc", "**/*.cxx"]
    if exclude_patterns is None:
        exclude_patterns = []

    # Learn what's defined inside the project so we can exclude it
    project_syms = scan_project_symbols(source_path, exclude_patterns)
    project_types = project_syms["types"]
    project_funcs = project_syms["functions"]

    src = Path(source_path)

    # Build a list of source files to analyse
    if source_file:
        src_files = [src / source_file]
    else:
        src_files = _collect_source_files(
            source_path, include_patterns, exclude_patterns
        )

    # Per-file: collect function calls, type refs, macro candidates
    all_functions: dict[str, tuple[int, str]] = {}    # name → (argc, raw_args)
    all_types: set[str] = set()
    all_enums: dict[str, dict] = {}
    all_structs: dict[str, str] = {}
    all_macros: set[str] = set()

    # Pre-read all source texts for two-pass analysis
    file_texts: dict[Path, str] = {}
    for fpath in src_files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        file_texts[fpath] = _strip_comments(text)

    # Pass 1: extract functions, types, enums, structs
    enum_values: set[str] = set()

    for fpath, text in file_texts.items():
        for name, argc, raw in _extract_function_calls(text):
            if name not in all_functions and name not in project_funcs:
                all_functions[name] = (argc, raw)

        for t in _extract_type_refs(text, project_types):
            all_types.add(t)

        name_vals = _extract_enums(text)
        for ename, ebody in name_vals.items():
            if ename in project_types:
                for vname in ebody.get("values", {}):
                    enum_values.add(vname)
                continue
            if ename not in all_enums:
                all_enums[ename] = ebody
                for vname in ebody.get("values", {}):
                    enum_values.add(vname)

        name_def = _extract_structs(text)
        for sname, sdef in name_def.items():
            if sname in project_types or f"struct {sname}" in project_types:
                continue
            if sname not in all_structs:
                all_structs[sname] = sdef

    # Pass 2: extract macro candidates with enum values known
    for fpath, text in file_texts.items():
        all_macros.update(_extract_macro_candidates(text, enum_values))

    # Build header stems for naming-convention matching
    hdr_stems: dict[str, str] = {}
    for hdr in missing_headers:
        stem = Path(hdr).stem
        hdr_stems[hdr] = stem

    # Match functions to headers by naming convention
    funcs_with_header: dict[str, dict] = {}
    funcs_no_header: dict[str, dict] = {}

    for fname, (argc, raw_args) in sorted(all_functions.items()):
        params = _build_params(argc)
        entry = {"return": "int", "params": params}
        matched = False
        for hdr, stem in hdr_stems.items():
            if _matches_header(fname, stem):
                entry["header"] = hdr
                matched = True
                break
        if matched:
            funcs_with_header[fname] = entry
            if verbose:
                click.echo(f"    function: {fname} → {entry['header']}")
        else:
            funcs_no_header[fname] = entry
            if verbose:
                click.echo(f"    function: {fname} → *general*")

    # Build type entry
    types_out: dict[str, str] = {}
    for tname in sorted(all_types):
        if tname in _C_BUILTIN_TYPES or tname in project_types:
            continue
        types_out[tname] = "int"
        if verbose:
            click.echo(f"    type: {tname} → int")

    # Build macro entry (ALL_CAPS → value "0" as placeholder)
    macros_out: dict[str, str] = {}
    for mname in sorted(all_macros):
        if mname in project_types:
            continue
        macros_out[mname] = "0"
        if verbose:
            click.echo(f"    macro: {mname} → 0")

    # Build result
    result = {
        "headers": dict(missing_headers),
        "types": types_out,
        "macros": macros_out,
        "enums": all_enums,
        "structs": all_structs,
        "functions": {**funcs_with_header, **funcs_no_header},
    }

    return result


def _strip_comments(text: str) -> str:
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'//.*', '', text)
    return text


def _extract_function_calls(text: str) -> list[tuple[str, int, str]]:
    """Return ``[(name, arg_count, raw_args), ...]``."""
    results: list[tuple[str, int, str]] = []
    i = 0
    length = len(text)

    while i < length:
        if text[i] in ('"', "'"):
            quote = text[i]
            i += 1
            while i < length and text[i] != quote:
                if text[i] == '\\':
                    i += 1
                i += 1
            i += 1
            continue

        if not (text[i].isalpha() or text[i] == '_'):
            i += 1
            continue

        j = i
        while j < length and (text[j].isalnum() or text[j] == '_'):
            j += 1
        ident = text[i:j]

        k = j
        while k < length and text[k] in (' ', '\t', '\n'):
            k += 1
        if k >= length or text[k] != '(':
            i = j
            continue

        if ident in _C_KEYWORDS or ident in _C_BUILTIN_TYPES:
            i = k + 1
            continue

        depth = 1
        pos = k + 1
        while pos < length and depth > 0:
            ch = text[pos]
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif ch in ('"', "'"):
                q = ch
                pos += 1
                while pos < length and text[pos] != q:
                    if text[pos] == '\\':
                        pos += 1
                    pos += 1
            pos += 1

        if depth == 0:
            args_text = text[k + 1:pos - 1].strip()
            argc = _count_top_level_commas(args_text)
            results.append((ident, argc, args_text))

        i = pos

    return results


def _count_top_level_commas(text: str) -> int:
    if not text or text == "void":
        return 0
    depth = 0
    count = 0
    for ch in text:
        if ch in ('(', '[', '{'):
            depth += 1
        elif ch in (')', ']', '}'):
            depth -= 1
        elif ch == ',' and depth == 0:
            count += 1
    return count + 1


def _build_params(argc: int) -> list[str]:
    if argc == 0:
        return []
    if argc == 1:
        return ["void* arg"]
    return [f"void* arg{i}" for i in range(argc)]


def _matches_header(name: str, header_stem: str) -> bool:
    if not header_stem:
        return False
    prefix = header_stem + "_"
    if name.startswith(prefix):
        return True
    if name.startswith(header_stem):
        rest = name[len(header_stem):]
        if rest and rest[0] in ("_",):
            return True
    return False


# ── Type reference extraction ─────────────────────────────────────────

_TYPE_DECL_RE = re.compile(
    r'(?:^|\n|;|{|})\s*'
    r'(?:const\s+|volatile\s+|static\s+|extern\s+)?'
    r'([a-zA-Z_]\w*(?:\s*const)?)'
    r'(?:\s+|\s*\*\s*|\s+[*]+\s+)'
    r'([a-zA-Z_]\w*)'
    r'\s*(?:\[|=|;|\(|{)'
)

_CAST_RE = re.compile(
    r'\(([a-zA-Z_]\w*(?:\s*\*)*)\)\s*(?:[a-zA-Z_]|&|\*|~|!|\d)'
)

_FUNC_RET_RE = re.compile(
    r'(?:^|\n|;|{|})\s*'
    r'(?:const\s+|volatile\s+|static\s+|extern\s+)?'
    r'([a-zA-Z_]\w*)'
    r'\s+'
    r'([a-zA-Z_]\w*)'
    r'\s*\('
)


def _extract_type_refs(text: str, project_types: set[str]) -> set[str]:
    types: set[str] = set()

    for m in _TYPE_DECL_RE.finditer(text):
        tname = m.group(1).strip()
        if tname not in _C_BUILTIN_TYPES and not tname.startswith("//"):
            if tname not in project_types:
                types.add(tname)

    for m in _CAST_RE.finditer(text):
        tname = m.group(1).strip().rstrip('*').strip()
        if tname and tname not in _C_BUILTIN_TYPES:
            if tname not in project_types:
                types.add(tname)

    for m in _FUNC_RET_RE.finditer(text):
        tname = m.group(1).strip()
        fname = m.group(2).strip()
        if (tname not in _C_BUILTIN_TYPES
                and fname not in _C_KEYWORDS):
            if tname not in project_types:
                types.add(tname)

    return types


# ── Macro candidate extraction ────────────────────────────────────────

_MACRO_RE = re.compile(
    r'(?:\b|\s)(\w{3,})\b'
)


def _extract_macro_candidates(text: str,
                               exclude: set[str] | None = None) -> set[str]:
    """Return set of macro-like identifiers.

    An identifier is considered macro-like if it is:
      * all-uppercase (e.g. ``ESP_OK``), OR
      * contains at least one underscore AND at least two
        uppercase letters (e.g. ``pdMS_TO_TICKS``).
    """
    if exclude is None:
        exclude = set()
    candidates: set[str] = set()
    for m in _MACRO_RE.finditer(text):
        name = m.group(1)
        if name in _C_KEYWORDS or name in _C_BUILTIN_TYPES:
            continue
        if name in exclude:
            continue
        if name.endswith("_t"):
            continue
        if name.isupper():
            candidates.add(name)
        elif "_" in name and sum(1 for c in name if c.isupper()) >= 2:
            candidates.add(name)
    return candidates


# ── Enum extraction ───────────────────────────────────────────────────

_ENUM_RE = re.compile(
    r'typedef\s+enum\s*\{'
    r'([^}]*)\}'
    r'\s*(\w+)\s*;'
)

_ENUM_VALUE_RE = re.compile(
    r'(\w+)\s*(?:=\s*([^,}]+))?'
)


def _extract_enums(text: str) -> dict[str, dict]:
    """Return ``{enum_name: {"values": {val_name: val, ...}}}``."""
    result: dict[str, dict] = {}
    for m in _ENUM_RE.finditer(text):
        body = m.group(1)
        ename = m.group(2)
        values: dict[str, str | int] = {}
        for vm in _ENUM_VALUE_RE.finditer(body):
            vname = vm.group(1)
            vval = vm.group(2)
            if vval:
                try:
                    values[vname] = int(vval)
                except ValueError:
                    values[vname] = vval.strip()
            else:
                values[vname] = -1 if not values else max(
                    v for v in values.values() if isinstance(v, int)
                ) + 1 if values else 0
        result[ename] = {"values": values}
    return result


# ── Struct extraction ─────────────────────────────────────────────────

_STRUCT_RE = re.compile(
    r'struct\s+(\w+)\s*\{'
    r'([^}]*)\}'
    r'\s*(\w+)?\s*;'
)


def _extract_structs(text: str) -> dict[str, str]:
    """Return ``{struct_name: "struct … { … };"}``."""
    result: dict[str, str] = {}
    for m in _STRUCT_RE.finditer(text):
        sname = m.group(3) if m.group(3) else m.group(1)
        definition = m.group(0)
        result[sname] = definition
    return result


# ── Source file collection ────────────────────────────────────────────


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
