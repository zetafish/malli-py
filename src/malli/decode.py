from __future__ import annotations

import uuid as _uuid
from typing import Any, Callable

from .core import _parse_schema, _parse_map_entries, validate

Decoder = Callable[[Any, dict, list], Any]
Transformer = dict[str, Decoder]


def _safe(fn: Callable[[Any], Any]) -> Decoder:
    def wrapped(v: Any, _props: dict, _children: list) -> Any:
        try:
            return fn(v)
        except (ValueError, TypeError):
            return v
    return wrapped


def _decode_int(v: Any) -> Any:
    if isinstance(v, str):
        return int(v)
    return v


def _decode_float(v: Any) -> Any:
    if isinstance(v, str):
        return float(v)
    return v


def _decode_bool(v: Any) -> Any:
    if isinstance(v, str):
        low = v.strip().lower()
        if low == "true":
            return True
        if low == "false":
            return False
    return v


def _decode_string(v: Any) -> Any:
    if v is None or isinstance(v, (list, tuple, dict, set, frozenset)):
        return v
    if isinstance(v, str):
        return v
    return str(v)


def _decode_uuid(v: Any) -> Any:
    if isinstance(v, str):
        return _uuid.UUID(v)
    return v


def _decode_set(v: Any, _props: dict, _children: list) -> Any:
    if isinstance(v, (list, tuple)):
        try:
            return set(v)
        except TypeError:
            return v
    return v


def _decode_tuple(v: Any, _props: dict, _children: list) -> Any:
    if isinstance(v, list):
        return tuple(v)
    return v


string_transformer: Transformer = {
    "int": _safe(_decode_int),
    "float": _safe(_decode_float),
    "bool": _safe(_decode_bool),
    "uuid": _safe(_decode_uuid),
    "string": _safe(_decode_string),
    "keyword": _safe(_decode_string),
    "symbol": _safe(_decode_string),
}


json_transformer: Transformer = {
    "int": _safe(_decode_int),
    "float": _safe(_decode_float),
    "uuid": _safe(_decode_uuid),
    "set": _decode_set,
    "tuple": _decode_tuple,
}


_COLLECTION_NAMES = {"vector", "sequential", "set", "tuple", "map-of", "map"}
_COMPOSITE_NAMES = {"and", "or", "maybe", "not", "enum"}


def _decode_children_and(v: Any, children: list, transformer: Transformer) -> Any:
    for c in children:
        v = decode(c, v, transformer)
    return v


def _decode_children_or(v: Any, children: list, transformer: Transformer) -> Any:
    for c in children:
        candidate = decode(c, v, transformer)
        if validate(c, candidate):
            return candidate
    return v


def _decode_collection(name: str, props: dict, children: list, v: Any, transformer: Transformer) -> Any:
    if name == "vector":
        if not isinstance(v, list):
            return v
        return [decode(children[0], x, transformer) for x in v]
    if name == "sequential":
        if isinstance(v, list):
            return [decode(children[0], x, transformer) for x in v]
        if isinstance(v, tuple):
            return tuple(decode(children[0], x, transformer) for x in v)
        return v
    if name == "set":
        if not isinstance(v, (set, frozenset)):
            return v
        return {decode(children[0], x, transformer) for x in v}
    if name == "tuple":
        if not isinstance(v, (list, tuple)) or len(v) != len(children):
            return v
        decoded = [decode(children[i], v[i], transformer) for i in range(len(children))]
        return type(v)(decoded) if isinstance(v, tuple) else decoded
    if name == "map-of":
        if not isinstance(v, dict):
            return v
        key_s, val_s = children
        return {
            decode(key_s, k, transformer): decode(val_s, val, transformer)
            for k, val in v.items()
        }
    if name == "map":
        if not isinstance(v, dict):
            return v
        entries = _parse_map_entries(children)
        out = dict(v)
        for key, _entry_props, sch in entries:
            if key in out:
                out[key] = decode(sch, out[key], transformer)
        return out
    return v


def decode(schema: Any, value: Any, transformer: Transformer) -> Any:
    name, props, children = _parse_schema(schema)

    if name == "maybe":
        if value is None:
            return None
        return decode(children[0], value, transformer)
    if name == "and":
        return _decode_children_and(value, children, transformer)
    if name == "or":
        return _decode_children_or(value, children, transformer)
    if name in ("enum", "not"):
        return value

    if name in _COLLECTION_NAMES:
        value = _decode_collection(name, props, children, value, transformer)

    decoder = transformer.get(name)
    if decoder is not None:
        value = decoder(value, props, children)

    return value


class _Invalid:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "INVALID"

    def __bool__(self) -> bool:
        return False


INVALID = _Invalid()


def parse(schema: Any, value: Any, transformer: Transformer | None = None) -> Any:
    if transformer is not None:
        value = decode(schema, value, transformer)
    if validate(schema, value):
        return value
    return INVALID
