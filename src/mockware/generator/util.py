from __future__ import annotations

import re

_DEFAULT_BODIES: dict[str, str] = {
    "void": "",
    "bool": "return false;",
    "int": "return 0;",
    "int32_t": "return 0;",
    "uint32_t": "return 0;",
    "int64_t": "return 0;",
    "uint64_t": "return 0;",
    "size_t": "return 0;",
    "ssize_t": "return 0;",
    "char": "return '\\0';",
    "float": "return 0.0f;",
    "double": "return 0.0;",
}

_FUNC_PTR_RE = re.compile(r"\(?\s*\*\s*(\w+)\s*\)?")


def auto_body(return_type: str) -> str:
    body = _DEFAULT_BODIES.get(return_type)
    if body is not None:
        return body
    if return_type.endswith("*"):
        return "return NULL;"
    if return_type.startswith("struct "):
        return f"return ({return_type}){{0}};"
    if return_type.startswith("enum "):
        return "return 0;"
    return "return 0;"


def extract_param_name(param: str, index: int) -> str:
    m = _FUNC_PTR_RE.search(param)
    if m:
        return m.group(1)
    parts = param.rsplit(None, 1)
    if len(parts) == 2:
        candidate = parts[1].lstrip("*").rstrip("[]")
        if candidate and not candidate.startswith("("):
            return candidate
    return f"arg{index}"


def arg_names(params: list[str]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for i, p in enumerate(params):
        name = extract_param_name(p, i)
        while name in seen:
            name = f"{name}_{i}"
        seen.add(name)
        names.append(name)
    return names


def params_str(params: list[str]) -> str:
    return ", ".join(params) if params else "void"


def split_member_var(var_str: str) -> tuple[str, str | None]:
    if "=" in var_str:
        parts = var_str.split("=", 1)
        return parts[0].strip(), parts[1].strip()
    return var_str.strip(), None
