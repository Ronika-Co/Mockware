from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Macro:
    value: str | None = None
    kind: str | None = None
    body: str | None = None


@dataclass
class EnumValues:
    values: dict[str, int | str] = field(default_factory=dict)


@dataclass
class TypeDef:
    underlying: str | None = None
    definition: str | None = None


@dataclass
class Function:
    return_type: str = "void"
    params: list[str] = field(default_factory=list)
    body: str | None = None


@dataclass
class Constructor:
    params: list[str] = field(default_factory=list)
    body: str | None = None
    init_list: list[str] = field(default_factory=list)


@dataclass
class Method:
    return_type: str = "void"
    params: list[str] = field(default_factory=list)
    body: str | None = None
    is_const: bool = False
    is_static: bool = False


@dataclass
class ClassDef:
    constructors: list[Constructor] = field(default_factory=list)
    destructor: str | None = None
    methods: dict[str, Method] = field(default_factory=dict)
    static_methods: dict[str, Method] = field(default_factory=dict)
    member_variables: dict[str, str] = field(default_factory=dict)


@dataclass
class Namespace:
    classes: dict[str, ClassDef] = field(default_factory=dict)
    enums: dict[str, EnumValues] = field(default_factory=dict)
    functions: dict[str, Function] = field(default_factory=dict)


@dataclass
class Header:
    language: str = "c"
    includes: list[str] = field(default_factory=list)
    system_includes: list[str] = field(default_factory=list)
    macros: dict[str, Macro] = field(default_factory=dict)
    types: dict[str, TypeDef] = field(default_factory=dict)
    enums: dict[str, EnumValues] = field(default_factory=dict)
    functions: dict[str, Function] = field(default_factory=dict)
    namespaces: dict[str, Namespace] = field(default_factory=dict)


@dataclass
class Config:
    headers: dict[str, Header] = field(default_factory=dict)
