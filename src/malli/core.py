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
