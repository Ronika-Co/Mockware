from __future__ import annotations

import subprocess
from pathlib import Path

import click
import pycparser
from pycparser import c_ast


def parse_headers(
    idf_path: str,
    headers: dict[str, list[str]],
    extra_includes: list[str],
    verbose: bool,
) -> dict[str, dict]:
    """Parse each header with pycparser and return structured YAML data."""
    comp_dir = Path(idf_path) / "components"
    inc_dirs = _all_include_dirs(idf_path, extra_includes)
    fake_dir = _find_fake_libc()

    result: dict[str, dict] = {}

    for comp_name, rels in headers.items():
        for rel in rels:
            hdr_path = comp_dir / comp_name / "include" / rel
            hdr_key = _header_key(comp_name, rel)

            if verbose:
                click.echo(f"  parsing {rel}…")

            preprocessed = _preprocess(hdr_path, inc_dirs, fake_dir, extra_includes)
            if preprocessed is None:
                if verbose:
                    click.echo("    └─ preprocessor failed, skipping")
                result.setdefault(hdr_key, _empty_entry())
                continue

            parsed = _parse(preprocessed, hdr_path)
            if parsed is None:
                if verbose:
                    click.echo("    └─ pycparser failed, skipping")
                result.setdefault(hdr_key, _empty_entry())
                continue

            data = _extract(parsed, hdr_path)
            result[hdr_key] = data

    return result


# ── Header key ──────────────────────────────────────────────────────────


def _header_key(comp_name: str, rel: str) -> str:
    if rel.startswith(comp_name):
        return rel
    return f"{comp_name}/{rel}"


def _empty_entry() -> dict:
    return {"includes": [], "macros": {}, "types": {},
            "enums": {}, "structs": {}, "functions": {}}


# ── Include dirs ────────────────────────────────────────────────────────


def _all_include_dirs(idf_path: str, extra: list[str]) -> list[str]:
    dirs = list(extra)
    comp_dir = Path(idf_path) / "components"
    if comp_dir.is_dir():
        for child in sorted(comp_dir.iterdir()):
            inc = child / "include"
            if inc.is_dir():
                dirs.append(str(inc))
    return dirs


def _find_fake_libc() -> str | None:
    """Locate pycparser's ``utils/fake_libc_include`` directory."""
    pkg_dir = Path(pycparser.__file__).parent
    candidates = [
        pkg_dir / "utils" / "fake_libc_include",
        pkg_dir.parent / "utils" / "fake_libc_include",
    ]
    for c in candidates:
        if c.is_dir():
            return str(c)
    return None


# ── Preprocessing ───────────────────────────────────────────────────────


# GCC builtins / attributes we want to strip so pycparser can handle them.
_STRIP_DEFINES = [
    "-D__attribute__(x)=",
    "-D__attribute(x)=",
    "-D__asm__(x)=",
    "-D__asm(x)=",
    "-D__inline__=",
    "-D__inline=",
    "-D__restrict=",
    "-D__restrict__=",
    "-D__volatile__=",
    "-D__volatile=",
    "-D__extension__=",
    "-D__builtin_va_list=void*",
    "-D__int128=long long",
    "-D__int128_t=long long",
    "-D__uint128_t=\"unsigned long long\"",
    "-D__builtin_offsetof(t,m)=((size_t)&((t*)0)->m)",
    "-D__builtin_va_arg(a,t)=((t)a)",
    "-D__builtin_va_start(a,v)=((void)0)",
    "-D__builtin_va_end(a)=((void)0)",
    "-D__builtin_va_copy(d,s)=((void)(d=s))",
    # ESP-IDF specific
    "-DIRAM_ATTR=",
    "-DIRAM_DATA_ATTR=",
    "-DIROM_ATTR=",
    "-DTCM_ATTR=",
    "-DNOINLINE_ATTR=",
    "-DWARN_UNUSED_RET_ATTR=",
]


def _preprocess(
    hdr_path: Path,
    inc_dirs: list[str],
    fake_dir: str | None,
    extra_includes: list[str],
) -> str | None:
    """Run ``gcc -E`` and return preprocessed C code."""
    try:
        cmd = ["gcc", "-E", "-x", "c", "-std=c11"]
        # Strip GCC extensions
        cmd.extend(_STRIP_DEFINES)
        # User-provided include dirs
        for d in inc_dirs:
            cmd.extend(["-I", d])
        # pycparser fake libc
        if fake_dir:
            cmd.extend(["-I", fake_dir])
        # Include path for the header itself
        cmd.extend(["-I", str(hdr_path.parent)])
        cmd.append(str(hdr_path))

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None
        return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


# ── pycparser parse ─────────────────────────────────────────────────────


def _parse(preprocessed: str, hdr_path: Path) -> c_ast.FileAST | None:
    """Feed preprocessed C into pycparser and return the AST."""
    try:
        return pycparser.parse(preprocessed, filename=str(hdr_path),
                               use_cpp=False)
    except Exception:
        return None


# ── AST walker ──────────────────────────────────────────────────────────


class _Extractor(c_ast.NodeVisitor):
    """Walks the AST and collects types, enums, structs, functions."""

    def __init__(self, hdr_path: Path) -> None:
        self.hdr_path = hdr_path
        self.hdr_text = hdr_path.read_text(encoding="utf-8", errors="replace")
        self.includes: list[str] = []
        self.types: dict[str, str] = {}
        self.enums: dict[str, dict] = {}
        self.structs: dict[str, dict] = {}
        self.functions: dict[str, dict] = {}
        self._seen_funcs: set[str] = set()

    def visit_Typedef(self, node: c_ast.Typedef) -> None:
        name = node.name
        underlying = node.type.type  # TypeDecl → actual type

        if isinstance(underlying, c_ast.Struct):
            struct = underlying
            if struct.name:
                sname = struct.name
            else:
                sname = name
            raw = self._extract_struct_raw(node)
            if raw:
                self.structs[sname] = {"definition": raw}
            self.types[name] = f"struct {sname}"
            # Also extract members from decls
            if struct.decls:
                members = []
                for m in struct.decls:
                    mname = m.name
                    mtype = self._type_str(m.type)
                    members.append({"name": mname, "type": mtype})
                if members:
                    if sname not in self.structs:
                        self.structs[sname] = {}
                    self.structs[sname]["members"] = members

        elif isinstance(underlying, c_ast.Enum):
            enum = underlying
            ename = enum.name or name
            if enum.values:
                vals: dict[str, str | int] = {}
                for v in enum.values:
                    if v.value:
                        vals[v.name] = v.value.value
                    else:
                        vals[v.name] = "/* auto */"
                self.enums[ename] = {"values": vals}
            self.types[name] = f"enum {ename}"

        elif isinstance(underlying, c_ast.Union):
            self.types[name] = f"union {underlying.name or name}"

        else:
            tstr = self._type_str(underlying)
            self.types[name] = tstr

    def visit_FuncDef(self, node: c_ast.FuncDef) -> None:
        """Handle function *definitions* (with body) — typically inline functions."""
        fname = node.decl.name
        if fname in self._seen_funcs:
            return
        self._seen_funcs.add(fname)

        ret_type = self._type_str(node.decl.type.type)
        params = []
        if node.decl.type.args:
            for p in node.decl.type.args.params:
                pname = p.name or ""
                ptype = self._type_str(p.type)
                params.append(f"{ptype} {pname}".strip())

        body = self._extract_inline_body(node)
        self.functions[fname] = {
            "kind": "inline",
            "return": ret_type,
            "params": params,
            "body": body,
        }

    def visit_Decl(self, node: c_ast.Decl) -> None:
        # Top-level function declarations
        if isinstance(node.type, c_ast.FuncDecl):
            fname = node.name
            if fname in self._seen_funcs:
                return
            self._seen_funcs.add(fname)

            ret_type = self._type_str(node.type.type)
            params = []
            if node.type.args:
                for p in node.type.args.params:
                    pname = p.name or ""
                    ptype = self._type_str(p.type)
                    params.append(f"{ptype} {pname}".strip())

            self.functions[fname] = {
                "return": ret_type,
                "params": params,
            }

        # Top-level struct/union/enum declarations
        if isinstance(node.type, c_ast.Struct):
            struct = node.type
            if struct.name:
                raw = self._extract_struct_raw(node)
                if raw:
                    self.structs[struct.name] = {"definition": raw}
        elif isinstance(node.type, c_ast.Union):
            pass
        elif isinstance(node.type, c_ast.Enum):
            enum = node.type
            if enum.name and enum.values:
                vals = {}
                for v in enum.values:
                    vals[v.name] = v.value.value if v.value else "/* auto */"
                self.enums[enum.name] = {"values": vals}

    def _type_str(self, node: c_ast.Node) -> str:
        """Convert a pycparser type node to a C type string."""
        if isinstance(node, c_ast.TypeDecl):
            # qualifiers like const, volatile, etc.
            quals = " ".join(node.quals) if node.quals else ""
            base = self._identifier_str(node.type)
            if quals:
                return f"{quals} {base}".strip()
            return base
        elif isinstance(node, c_ast.PtrDecl):
            points_to = self._type_str(node.type)
            return f"{points_to}*"
        elif isinstance(node, c_ast.ArrayDecl):
            elem = self._type_str(node.type)
            dim = node.dim.value if node.dim else ""
            return f"{elem}[{dim}]"
        elif isinstance(node, c_ast.FuncDecl):
            ret = self._type_str(node.type)
            return f"{ret} (*)(...)"
        elif isinstance(node, c_ast.Struct):
            return f"struct {node.name or '{{...}}'}"
        elif isinstance(node, c_ast.Union):
            return f"union {node.name or '{{...}}'}"
        elif isinstance(node, c_ast.Enum):
            return f"enum {node.name or '{{...}}'}"
        elif isinstance(node, c_ast.IdentifierType):
            return " ".join(node.names)
        elif isinstance(node, c_ast.Typedef):
            return node.name
        elif isinstance(node, c_ast.TypeDecl):
            quals = " ".join(node.quals) if node.quals else ""
            base = self._type_str(node.type)
            return f"{quals} {base}".strip()
        return str(type(node).__name__)

    def _identifier_str(self, node: c_ast.Node) -> str:
        if isinstance(node, c_ast.IdentifierType):
            return " ".join(node.names)
        return self._type_str(node)

    def _extract_struct_raw(self, node: c_ast.Node) -> str | None:
        """Extract the raw ``typedef struct { ... } name;`` from source."""
        try:
            start = node.coord.line
        except AttributeError:
            return None

        # Walk the header text from the start line to find matching braces
        lines = self.hdr_text.splitlines()
        if start < 1 or start > len(lines):
            return None

        depth = 0
        started = False
        collected: list[str] = []
        for i, line in enumerate(lines[start - 1:], start=start):
            stripped = line
            for ch in stripped:
                if ch == '{':
                    depth += 1
                    started = True
                elif ch == '}':
                    depth -= 1
            collected.append(stripped)
            if started and depth == 0:
                break

        raw = "\n".join(collected).strip()
        return raw if raw else None

    def _extract_inline_body(self, node: c_ast.FuncDef) -> str:
        """Extract the full inline function definition from source text."""
        try:
            start = node.coord.line
        except AttributeError:
            return ""
        # Walk up to the closing brace
        lines = self.hdr_text.splitlines()
        if start < 1 or start > len(lines):
            return ""
        depth = 0
        started = False
        collected: list[str] = []
        for i, line in enumerate(lines[start - 1:], start=start):
            stripped = line
            for ch in stripped:
                if ch == '{':
                    depth += 1
                    started = True
                elif ch == '}':
                    depth -= 1
            collected.append(stripped)
            if started and depth == 0:
                break
        return "\n".join(collected)


def _extract(ast: c_ast.FileAST, hdr_path: Path) -> dict:
    """Run the extractor and return the data dict for one header."""
    ext = _Extractor(hdr_path)
    ext.visit(ast)

    return {
        "includes": ext.includes,
        "macros": {},
        "types": ext.types,
        "enums": ext.enums,
        "structs": ext.structs,
        "functions": ext.functions,
    }
