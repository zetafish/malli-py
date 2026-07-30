from __future__ import annotations

from typing import Any

from .core import _parse_schema


def _format_path(in_: list) -> str:
    parts: list[str] = []
    for step in in_:
        if isinstance(step, int) and not isinstance(step, bool):
            parts.append(f"[{step}]")
        elif isinstance(step, str):
            parts.append(step if not parts else f".{step}")
        else:
            parts.append(f"[{step!r}]")
    return "".join(parts)


def _bounds_suffix(props: dict, unit: str = "") -> str:
    lo = props.get("min")
    hi = props.get("max")
    unit = f" {unit}" if unit else ""
    if lo is not None and hi is not None:
        return f" between {lo} and {hi}{unit}"
    if lo is not None:
        return f" at least {lo}{unit}"
    if hi is not None:
        return f" at most {hi}{unit}"
    return ""


def _msg_int(props: dict, _children: list) -> str:
    return "should be an int" + _bounds_suffix(props)


def _msg_float(props: dict, _children: list) -> str:
    return "should be a float" + _bounds_suffix(props)


def _msg_string(props: dict, _children: list) -> str:
    return "should be a string" + _bounds_suffix(props, unit="characters long")


def _msg_bool(_props: dict, _children: list) -> str:
    return "should be a boolean"


def _msg_nil(_props: dict, _children: list) -> str:
    return "should be nil"


def _msg_some(_props: dict, _children: list) -> str:
    return "should not be nil"


def _msg_any(_props: dict, _children: list) -> str:
    return "invalid"


def _msg_uuid(_props: dict, _children: list) -> str:
    return "should be a UUID"


def _msg_re(props: dict, children: list) -> str:
    pattern = props.get("pattern") if props else None
    if pattern is None and children:
        pattern = children[0]
    return f"should match pattern {pattern}"


def _msg_enum(_props: dict, children: list) -> str:
    return "should be one of " + ", ".join(repr(c) for c in children)


def _msg_not(_props: dict, children: list) -> str:
    if children:
        return f"should not match {children[0]!r}"
    return "invalid"


def _msg_vector(_props: dict, _children: list) -> str:
    return "should be a vector"


def _msg_sequential(_props: dict, _children: list) -> str:
    return "should be a list or tuple"


def _msg_set(_props: dict, _children: list) -> str:
    return "should be a set"


def _msg_tuple(_props: dict, children: list) -> str:
    return f"should be a tuple of {len(children)} element(s)"


def _msg_map(_props: dict, _children: list) -> str:
    return "should be a map"


def _msg_map_of(_props: dict, _children: list) -> str:
    return "should be a map"


_MESSAGES = {
    "int": _msg_int,
    "float": _msg_float,
    "string": _msg_string,
    "keyword": _msg_string,
    "symbol": _msg_string,
    "bool": _msg_bool,
    "nil": _msg_nil,
    "some": _msg_some,
    "any": _msg_any,
    "uuid": _msg_uuid,
    "re": _msg_re,
    "enum": _msg_enum,
    "not": _msg_not,
    "vector": _msg_vector,
    "sequential": _msg_sequential,
    "set": _msg_set,
    "tuple": _msg_tuple,
    "map": _msg_map,
    "map-of": _msg_map_of,
}


def _message(error: dict) -> str:
    tag = error.get("type")
    if tag == "missing-key":
        return "missing required key"
    if tag == "extra-key":
        return "should not be present"
    try:
        name, props, children = _parse_schema(error["schema"])
    except TypeError:
        return "invalid"
    fn = _MESSAGES.get(name)
    if fn is None:
        return "invalid"
    return fn(props, children)


def humanize(explanation: dict | None) -> dict[str, str] | None:
    if explanation is None:
        return None
    result: dict[str, str] = {}
    for err in explanation.get("errors", []):
        key = _format_path(err.get("in", []))
        msg = _message(err)
        if key in result:
            result[key] = f"{result[key]} and {msg}"
        else:
            result[key] = msg
    return result or None
