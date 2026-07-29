from __future__ import annotations

import re as _re
import uuid as _uuid
from functools import lru_cache
from typing import Any, Callable

SimpleValidator = Callable[[Any, Any], bool]
CompositeValidator = Callable[[Any, tuple], bool]
CompositeExplainer = Callable[[Any, tuple, list, list], list]

_REGISTRY: dict[str, SimpleValidator] = {}
_COMPOSITES: dict[str, tuple[CompositeValidator, CompositeExplainer]] = {}


class UnknownSchemaError(KeyError):
    pass


def register(name: str, fn: SimpleValidator) -> None:
    _REGISTRY[name] = fn


def register_composite(name: str, v: CompositeValidator, e: CompositeExplainer) -> None:
    _COMPOSITES[name] = (v, e)


def _parse_schema(schema: Any) -> tuple[str, dict, list]:
    if isinstance(schema, str):
        return schema, {}, []
    if isinstance(schema, (list, tuple)) and len(schema) >= 1 and isinstance(schema[0], str):
        name = schema[0]
        rest = list(schema[1:])
        if rest and isinstance(rest[0], dict):
            return name, rest[0], rest[1:]
        return name, {}, rest
    raise TypeError(f"invalid schema: {schema!r}")


def _scalar_arg(props: dict, children: list) -> Any:
    if props:
        return props
    if children:
        return children[0]
    return {}


def validate(schema: Any, value: Any) -> bool:
    name, props, children = _parse_schema(schema)
    comp = _COMPOSITES.get(name)
    if comp is not None:
        return comp[0](value, (name, props, children))
    fn = _REGISTRY.get(name)
    if fn is None:
        raise UnknownSchemaError(name)
    return fn(value, _scalar_arg(props, children))


def _explain_impl(schema: Any, value: Any, path: list, in_: list) -> list:
    name, props, children = _parse_schema(schema)
    comp = _COMPOSITES.get(name)
    if comp is not None:
        return comp[1](value, (name, props, children), path, in_)
    fn = _REGISTRY.get(name)
    if fn is None:
        raise UnknownSchemaError(name)
    if fn(value, _scalar_arg(props, children)):
        return []
    return [{"path": path, "in": in_, "schema": schema, "value": value}]


def explain(schema: Any, value: Any) -> dict | None:
    errors = _explain_impl(schema, value, [], [])
    if not errors:
        return None
    return {"value": value, "schema": schema, "errors": errors}


def _check_bounds(v: float | int, props: dict) -> bool:
    if not isinstance(props, dict):
        return True
    lo = props.get("min")
    hi = props.get("max")
    if lo is not None and v < lo:
        return False
    if hi is not None and v > hi:
        return False
    return True


def _v_int(v: Any, props: Any) -> bool:
    if isinstance(v, bool) or not isinstance(v, int):
        return False
    return _check_bounds(v, props)


def _v_float(v: Any, props: Any) -> bool:
    if not isinstance(v, float):
        return False
    return _check_bounds(v, props)


def _v_string(v: Any, props: Any) -> bool:
    if not isinstance(v, str):
        return False
    if isinstance(props, dict):
        lo = props.get("min")
        hi = props.get("max")
        n = len(v)
        if lo is not None and n < lo:
            return False
        if hi is not None and n > hi:
            return False
    return True


def _v_bool(v: Any, _props: Any) -> bool:
    return isinstance(v, bool)


def _v_nil(v: Any, _props: Any) -> bool:
    return v is None


def _v_any(_v: Any, _props: Any) -> bool:
    return True


def _v_some(v: Any, _props: Any) -> bool:
    return v is not None


def _v_uuid(v: Any, _props: Any) -> bool:
    return isinstance(v, _uuid.UUID)


@lru_cache(maxsize=256)
def _compile(pattern: str) -> _re.Pattern[str]:
    return _re.compile(pattern)


def _v_re(v: Any, arg: Any) -> bool:
    if not isinstance(v, str):
        return False
    if isinstance(arg, dict):
        pattern = arg.get("pattern")
    else:
        pattern = arg
    if not isinstance(pattern, str):
        raise TypeError(f":re schema requires a string pattern, got {pattern!r}")
    return _compile(pattern).fullmatch(v) is not None


register("int", _v_int)
register("float", _v_float)
register("string", _v_string)
register("bool", _v_bool)
register("nil", _v_nil)
register("any", _v_any)
register("some", _v_some)
register("uuid", _v_uuid)
register("keyword", _v_string)
register("symbol", _v_string)
register("re", _v_re)


def _require_min_children(name: str, children: list, n: int) -> None:
    if len(children) < n:
        raise TypeError(f"{name!r} expects at least {n} child schema(s), got {len(children)}")


def _require_exact_children(name: str, children: list, n: int) -> None:
    if len(children) != n:
        raise TypeError(f"{name!r} expects exactly {n} child schema(s), got {len(children)}")


def _v_and(v: Any, schema: tuple) -> bool:
    _, _, children = schema
    _require_min_children("and", children, 1)
    return all(validate(c, v) for c in children)


def _e_and(v: Any, schema: tuple, path: list, in_: list) -> list:
    _, _, children = schema
    _require_min_children("and", children, 1)
    errs = []
    for i, c in enumerate(children):
        errs.extend(_explain_impl(c, v, path + [i], in_))
    return errs


def _v_or(v: Any, schema: tuple) -> bool:
    _, _, children = schema
    _require_min_children("or", children, 1)
    return any(validate(c, v) for c in children)


def _e_or(v: Any, schema: tuple, path: list, in_: list) -> list:
    _, _, children = schema
    _require_min_children("or", children, 1)
    all_errs = []
    for i, c in enumerate(children):
        e = _explain_impl(c, v, path + [i], in_)
        if not e:
            return []
        all_errs.extend(e)
    return all_errs


def _v_enum(v: Any, schema: tuple) -> bool:
    _, _, children = schema
    _require_min_children("enum", children, 1)
    return v in children


def _e_enum(v: Any, schema: tuple, path: list, in_: list) -> list:
    name, props, children = schema
    _require_min_children("enum", children, 1)
    if v in children:
        return []
    original = [name] + ([props] if props else []) + list(children)
    return [{"path": path, "in": in_, "schema": original, "value": v}]


def _v_maybe(v: Any, schema: tuple) -> bool:
    _, _, children = schema
    _require_exact_children("maybe", children, 1)
    return v is None or validate(children[0], v)


def _e_maybe(v: Any, schema: tuple, path: list, in_: list) -> list:
    _, _, children = schema
    _require_exact_children("maybe", children, 1)
    if v is None:
        return []
    return _explain_impl(children[0], v, path + [0], in_)


def _v_not(v: Any, schema: tuple) -> bool:
    _, _, children = schema
    _require_exact_children("not", children, 1)
    return not validate(children[0], v)


def _e_not(v: Any, schema: tuple, path: list, in_: list) -> list:
    name, props, children = schema
    _require_exact_children("not", children, 1)
    if not validate(children[0], v):
        return []
    original = [name] + ([props] if props else []) + list(children)
    return [{"path": path, "in": in_, "schema": original, "value": v}]


register_composite("and", _v_and, _e_and)
register_composite("or", _v_or, _e_or)
register_composite("enum", _v_enum, _e_enum)
register_composite("maybe", _v_maybe, _e_maybe)
register_composite("not", _v_not, _e_not)


def _check_size_bounds(n: int, props: dict) -> bool:
    lo = props.get("min")
    hi = props.get("max")
    if lo is not None and n < lo:
        return False
    if hi is not None and n > hi:
        return False
    return True


def _reconstruct(name: str, props: dict, children: list) -> Any:
    if not props and not children:
        return name
    if props:
        return [name, props, *children]
    return [name, *children]


def _collection_error(name: str, props: dict, children: list, path: list, in_: list, value: Any) -> dict:
    return {"path": path, "in": in_, "schema": _reconstruct(name, props, children), "value": value}


def _v_vector(v: Any, schema: tuple) -> bool:
    name, props, children = schema
    _require_exact_children(name, children, 1)
    if not isinstance(v, list):
        return False
    if not _check_size_bounds(len(v), props):
        return False
    return all(validate(children[0], item) for item in v)


def _e_vector(v: Any, schema: tuple, path: list, in_: list) -> list:
    name, props, children = schema
    _require_exact_children(name, children, 1)
    if not isinstance(v, list) or not _check_size_bounds(len(v), props):
        return [_collection_error(name, props, children, path, in_, v)]
    errs = []
    for i, item in enumerate(v):
        errs.extend(_explain_impl(children[0], item, path + [0], in_ + [i]))
    return errs


def _v_sequential(v: Any, schema: tuple) -> bool:
    name, props, children = schema
    _require_exact_children(name, children, 1)
    if not isinstance(v, (list, tuple)):
        return False
    if not _check_size_bounds(len(v), props):
        return False
    return all(validate(children[0], item) for item in v)


def _e_sequential(v: Any, schema: tuple, path: list, in_: list) -> list:
    name, props, children = schema
    _require_exact_children(name, children, 1)
    if not isinstance(v, (list, tuple)) or not _check_size_bounds(len(v), props):
        return [_collection_error(name, props, children, path, in_, v)]
    errs = []
    for i, item in enumerate(v):
        errs.extend(_explain_impl(children[0], item, path + [0], in_ + [i]))
    return errs


def _v_set(v: Any, schema: tuple) -> bool:
    name, props, children = schema
    _require_exact_children(name, children, 1)
    if not isinstance(v, (set, frozenset)):
        return False
    if not _check_size_bounds(len(v), props):
        return False
    return all(validate(children[0], item) for item in v)


def _e_set(v: Any, schema: tuple, path: list, in_: list) -> list:
    name, props, children = schema
    _require_exact_children(name, children, 1)
    if not isinstance(v, (set, frozenset)) or not _check_size_bounds(len(v), props):
        return [_collection_error(name, props, children, path, in_, v)]
    errs = []
    for item in v:
        errs.extend(_explain_impl(children[0], item, path + [0], in_ + [item]))
    return errs


def _v_tuple(v: Any, schema: tuple) -> bool:
    _, _, children = schema
    if not isinstance(v, (list, tuple)):
        return False
    if len(v) != len(children):
        return False
    return all(validate(children[i], v[i]) for i in range(len(children)))


def _e_tuple(v: Any, schema: tuple, path: list, in_: list) -> list:
    name, props, children = schema
    if not isinstance(v, (list, tuple)) or len(v) != len(children):
        return [_collection_error(name, props, children, path, in_, v)]
    errs = []
    for i, child in enumerate(children):
        errs.extend(_explain_impl(child, v[i], path + [i], in_ + [i]))
    return errs


def _v_map_of(v: Any, schema: tuple) -> bool:
    name, props, children = schema
    _require_exact_children(name, children, 2)
    if not isinstance(v, dict):
        return False
    if not _check_size_bounds(len(v), props):
        return False
    key_s, val_s = children
    return all(validate(key_s, k) and validate(val_s, val) for k, val in v.items())


def _e_map_of(v: Any, schema: tuple, path: list, in_: list) -> list:
    name, props, children = schema
    _require_exact_children(name, children, 2)
    if not isinstance(v, dict) or not _check_size_bounds(len(v), props):
        return [_collection_error(name, props, children, path, in_, v)]
    key_s, val_s = children
    errs = []
    for k, val in v.items():
        errs.extend(_explain_impl(key_s, k, path + [0], in_ + [k]))
        errs.extend(_explain_impl(val_s, val, path + [1], in_ + [k]))
    return errs


register_composite("vector", _v_vector, _e_vector)
register_composite("sequential", _v_sequential, _e_sequential)
register_composite("set", _v_set, _e_set)
register_composite("tuple", _v_tuple, _e_tuple)
register_composite("map-of", _v_map_of, _e_map_of)


def _parse_map_entries(children: list) -> list[tuple[str, dict, Any]]:
    entries = []
    seen: set[str] = set()
    for entry in children:
        if not isinstance(entry, (list, tuple)) or len(entry) not in (2, 3):
            raise TypeError(f"invalid :map entry: {entry!r} (expected [key, schema] or [key, props, schema])")
        if len(entry) == 2:
            key, sch = entry
            props: dict = {}
        else:
            key, props, sch = entry
            if not isinstance(props, dict):
                raise TypeError(f"invalid :map entry props: {props!r} (expected dict)")
        if not isinstance(key, str):
            raise TypeError(f"invalid :map entry key: {key!r} (must be str)")
        if key in seen:
            raise TypeError(f"duplicate :map entry key: {key!r}")
        seen.add(key)
        entries.append((key, props, sch))
    return entries


def _v_map(v: Any, schema: tuple) -> bool:
    _, props, children = schema
    if not isinstance(v, dict):
        return False
    entries = _parse_map_entries(children)
    known: set[str] = set()
    for key, entry_props, sch in entries:
        known.add(key)
        if key in v:
            if not validate(sch, v[key]):
                return False
        elif not entry_props.get("optional"):
            return False
    if props.get("closed"):
        for k in v:
            if k not in known:
                return False
    return True


def _e_map(v: Any, schema: tuple, path: list, in_: list) -> list:
    name, props, children = schema
    if not isinstance(v, dict):
        return [_collection_error(name, props, children, path, in_, v)]
    entries = _parse_map_entries(children)
    known: set[str] = set()
    errs = []
    for key, entry_props, sch in entries:
        known.add(key)
        if key in v:
            errs.extend(_explain_impl(sch, v[key], path + [key], in_ + [key]))
        elif not entry_props.get("optional"):
            errs.append({
                "path": path + [key],
                "in": in_ + [key],
                "schema": sch,
                "value": None,
                "type": "missing-key",
            })
    if props.get("closed"):
        map_schema = _reconstruct(name, props, children)
        for k, val in v.items():
            if k not in known:
                errs.append({
                    "path": path + [k],
                    "in": in_ + [k],
                    "schema": map_schema,
                    "value": val,
                    "type": "extra-key",
                })
    return errs


register_composite("map", _v_map, _e_map)
