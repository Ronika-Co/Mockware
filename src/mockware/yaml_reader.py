from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import (
    ClassDef,
    Config,
    Constructor,
    EnumValues,
    Function,
    Header,
    Macro,
    Method,
    Namespace,
    TypeDef,
)


def read_config(path: str | Path) -> Config:
    raw = _load_yaml(path)
    headers_raw = raw.get("headers", {})
    headers: dict[str, Header] = {}
    for hdr_path, hdr_raw in headers_raw.items():
        headers[hdr_path] = _parse_header(hdr_raw)
    return Config(headers=headers)


def read_configs(paths: list[Path]) -> Config:
    headers: dict[str, Header] = {}
    for path in paths:
        config = read_config(path)
        for hdr_path, header in config.headers.items():
            if hdr_path in headers:
                headers[hdr_path] = _merge_headers(headers[hdr_path], header)
            else:
                headers[hdr_path] = header
    return Config(headers=headers)


def _load_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _merge_headers(base: Header, override: Header) -> Header:
    return Header(
        language=override.language or base.language,
        includes=_dedup_list(base.includes + override.includes),
        system_includes=_dedup_list(base.system_includes + override.system_includes),
        macros={**base.macros, **override.macros},
        types={**base.types, **override.types},
        enums={**base.enums, **override.enums},
        functions={**base.functions, **override.functions},
        namespaces={**base.namespaces, **override.namespaces},
    )


def _dedup_list(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _parse_header(raw: dict[str, Any]) -> Header:
    return Header(
        language=raw.get("language", "c"),
        includes=raw.get("includes") or [],
        system_includes=raw.get("system_includes") or [],
        macros=_parse_macros(raw.get("macros") or {}),
        types=_parse_types(raw.get("types") or {}),
        enums=_parse_enums(raw.get("enums") or {}),
        functions=_parse_functions(raw.get("functions") or {}),
        namespaces=_parse_namespaces(raw.get("namespaces") or {}),
    )


def _parse_macros(raw: dict[str, Any]) -> dict[str, Macro]:
    result: dict[str, Macro] = {}
    for name, value in raw.items():
        if isinstance(value, str):
            result[name] = Macro(value=value)
        elif isinstance(value, dict):
            result[name] = Macro(
                kind=value.get("kind"),
                body=value.get("body"),
            )
    return result


def _parse_types(raw: dict[str, Any]) -> dict[str, TypeDef]:
    result: dict[str, TypeDef] = {}
    for name, value in raw.items():
        if isinstance(value, str):
            result[name] = TypeDef(underlying=value)
        elif isinstance(value, dict):
            result[name] = TypeDef(definition=value.get("definition"))
    return result


def _parse_enums(raw: dict[str, Any]) -> dict[str, EnumValues]:
    result: dict[str, EnumValues] = {}
    for name, value in raw.items():
        if isinstance(value, dict):
            result[name] = EnumValues(values=value.get("values") or {})
    return result


def _parse_functions(raw: dict[str, Any]) -> dict[str, Function]:
    result: dict[str, Function] = {}
    for name, value in raw.items():
        if isinstance(value, dict):
            result[name] = Function(
                return_type=value.get("return", "void"),
                params=value.get("params") or [],
                body=value.get("body"),
            )
    return result


def _parse_namespaces(raw: dict[str, Any]) -> dict[str, Namespace]:
    result: dict[str, Namespace] = {}
    for ns_name, ns_raw in raw.items():
        result[ns_name] = Namespace(
            classes=_parse_classes(ns_raw.get("classes") or {}),
            enums=_parse_enums(ns_raw.get("enums") or {}),
            functions=_parse_functions(ns_raw.get("functions") or {}),
        )
    return result


def _parse_classes(raw: dict[str, Any]) -> dict[str, ClassDef]:
    result: dict[str, ClassDef] = {}
    for cls_name, cls_raw in raw.items():
        result[cls_name] = ClassDef(
            constructors=_parse_constructors(cls_raw.get("constructors") or []),
            destructor=cls_raw.get("destructor"),
            methods=_parse_methods(cls_raw.get("methods") or {}),
            static_methods=_parse_methods(cls_raw.get("static_methods") or {}),
            member_variables=dict(cls_raw.get("member_variables") or {}),
        )
    return result


def _parse_constructors(raw: list[Any]) -> list[Constructor]:
    result: list[Constructor] = []
    for entry in raw:
        if isinstance(entry, dict):
            result.append(
                Constructor(
                    params=entry.get("params") or [],
                    body=entry.get("body"),
                    init_list=entry.get("init_list") or [],
                )
            )
        elif isinstance(entry, list):
            result.append(Constructor(params=list(entry)))
    return result


def _parse_methods(raw: dict[str, Any]) -> dict[str, Method]:
    result: dict[str, Method] = {}
    for name, value in raw.items():
        if isinstance(value, dict):
            result[name] = Method(
                return_type=value.get("return", "void"),
                params=value.get("params") or [],
                body=value.get("body"),
                is_const=value.get("const", False),
                is_static=value.get("static", False),
            )
    return result
