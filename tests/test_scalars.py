import uuid

import pytest

import malli as m


@pytest.mark.parametrize(
    "schema,value,expected",
    [
        ("int", 0, True),
        ("int", -5, True),
        ("int", 3, True),
        ("int", 3.0, False),
        ("int", "3", False),
        ("int", True, False),
        ("int", False, False),
        ("int", None, False),
        (["int", {"min": 0}], 0, True),
        (["int", {"min": 0}], -1, False),
        (["int", {"max": 10}], 10, True),
        (["int", {"max": 10}], 11, False),
        (["int", {"min": 0, "max": 10}], 5, True),
        (["int", {"min": 0, "max": 10}], -1, False),
        (["int", {"min": 0, "max": 10}], 11, False),
    ],
)
def test_int(schema, value, expected):
    assert m.validate(schema, value) is expected


@pytest.mark.parametrize(
    "schema,value,expected",
    [
        ("float", 0.0, True),
        ("float", -1.5, True),
        ("float", 0, False),
        ("float", True, False),
        ("float", "1.0", False),
        (["float", {"min": 0.0}], 0.0, True),
        (["float", {"min": 0.0}], -0.1, False),
        (["float", {"max": 1.0}], 1.0, True),
        (["float", {"max": 1.0}], 1.1, False),
    ],
)
def test_float(schema, value, expected):
    assert m.validate(schema, value) is expected


@pytest.mark.parametrize(
    "schema,value,expected",
    [
        ("string", "", True),
        ("string", "hi", True),
        ("string", 3, False),
        ("string", None, False),
        (["string", {"min": 1}], "", False),
        (["string", {"min": 1}], "a", True),
        (["string", {"max": 3}], "abc", True),
        (["string", {"max": 3}], "abcd", False),
        (["string", {"min": 2, "max": 4}], "ab", True),
        (["string", {"min": 2, "max": 4}], "a", False),
        (["string", {"min": 2, "max": 4}], "abcde", False),
    ],
)
def test_string(schema, value, expected):
    assert m.validate(schema, value) is expected


@pytest.mark.parametrize(
    "value,expected",
    [(True, True), (False, True), (0, False), (1, False), (None, False), ("true", False)],
)
def test_bool(value, expected):
    assert m.validate("bool", value) is expected


@pytest.mark.parametrize(
    "value,expected",
    [(None, True), (0, False), ("", False), (False, False)],
)
def test_nil(value, expected):
    assert m.validate("nil", value) is expected


@pytest.mark.parametrize("value", [None, 0, "", [], {}, object()])
def test_any(value):
    assert m.validate("any", value) is True


@pytest.mark.parametrize(
    "value,expected",
    [(None, False), (0, True), ("", True), (False, True), ([], True)],
)
def test_some(value, expected):
    assert m.validate("some", value) is expected


def test_uuid():
    assert m.validate("uuid", uuid.uuid4()) is True
    assert m.validate("uuid", str(uuid.uuid4())) is False
    assert m.validate("uuid", None) is False


@pytest.mark.parametrize("name", ["keyword", "symbol"])
def test_keyword_symbol_alias_string(name):
    assert m.validate(name, "hello") is True
    assert m.validate(name, 3) is False


@pytest.mark.parametrize(
    "pattern,value,expected",
    [
        (r"^\d+$", "42", True),
        (r"^\d+$", "4a", False),
        (r"^\d+$", "", False),
        (r"[a-z]+", "abc", True),
        (r"[a-z]+", "abc1", False),
        (r"^\d+$", 42, False),
    ],
)
def test_re(pattern, value, expected):
    assert m.validate(["re", pattern], value) is expected


def test_re_dict_form():
    assert m.validate(["re", {"pattern": r"^\d+$"}], "42") is True


def test_tuple_schema_form():
    assert m.validate(("int", {"min": 0}), 5) is True
    assert m.validate(("int", {"min": 0}), -1) is False


def test_unknown_schema_raises():
    with pytest.raises(m.UnknownSchemaError):
        m.validate("nope", 1)


def test_invalid_schema_raises():
    with pytest.raises(TypeError):
        m.validate(123, 1)


def test_custom_register():
    m.register("pos-int", lambda v, _p: isinstance(v, int) and not isinstance(v, bool) and v > 0)
    assert m.validate("pos-int", 1) is True
    assert m.validate("pos-int", 0) is False
