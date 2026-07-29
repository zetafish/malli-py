from __future__ import annotations

import re as _re
import uuid as _uuid
from functools import lru_cache
from typing import Any, Callable

Validator = Callable[[Any, Any], bool]

_REGISTRY: dict[str, Validator] = {}


class UnknownSchemaError(KeyError):
    pass


def register(name: str, fn: Validator) -> None:
    _REGISTRY[name] = fn


def _parse_schema(schema: Any) -> tuple[str, Any]:
    if isinstance(schema, str):
        return schema, {}
    if isinstance(schema, (list, tuple)) and len(schema) >= 1 and isinstance(schema[0], str):
        if len(schema) == 1:
            return schema[0], {}
        return schema[0], schema[1]
    raise TypeError(f"invalid schema: {schema!r}")


def validate(schema: Any, value: Any) -> bool:
    name, arg = _parse_schema(schema)
    fn = _REGISTRY.get(name)
    if fn is None:
        raise UnknownSchemaError(name)
    return fn(value, arg)


def explain(schema: Any, value: Any) -> dict | None:
    name, arg = _parse_schema(schema)
    fn = _REGISTRY.get(name)
    if fn is None:
        raise UnknownSchemaError(name)
    if fn(value, arg):
        return None
    return {
        "value": value,
        "schema": schema,
        "errors": [{"path": [], "in": [], "schema": schema, "value": value}],
    }


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
