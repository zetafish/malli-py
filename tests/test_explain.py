import uuid

import pytest

import malli as m


@pytest.mark.parametrize(
    "schema,value",
    [
        ("int", 3),
        (["int", {"min": 0, "max": 10}], 5),
        ("float", 1.5),
        ("string", "hi"),
        (["string", {"min": 1}], "a"),
        ("bool", True),
        ("nil", None),
        ("any", object()),
        ("some", 0),
        ("uuid", uuid.uuid4()),
        (["re", r"^\d+$"], "42"),
    ],
)
def test_explain_none_when_valid(schema, value):
    assert m.explain(schema, value) is None


def _single_error(schema, value):
    result = m.explain(schema, value)
    assert result is not None
    assert result["value"] == value
    assert result["schema"] == schema
    assert len(result["errors"]) == 1
    err = result["errors"][0]
    assert err["path"] == []
    assert err["in"] == []
    assert err["schema"] == schema
    assert err["value"] == value
    return err


def test_explain_int_type_mismatch():
    _single_error("int", "3")


def test_explain_int_bound_violation():
    _single_error(["int", {"min": 0}], -1)


def test_explain_string_min_length():
    _single_error(["string", {"min": 2}], "a")


def test_explain_re_mismatch():
    _single_error(["re", r"^\d+$"], "abc")


def test_explain_some_on_none():
    _single_error("some", None)


def test_explain_uuid_on_string():
    _single_error("uuid", "not-a-uuid")


def test_explain_bare_string_schema_preserved():
    result = m.explain("int", "x")
    assert result["schema"] == "int"
    assert result["errors"][0]["schema"] == "int"


def test_explain_list_schema_preserved():
    schema = ["int", {"min": 0}]
    result = m.explain(schema, -1)
    assert result["schema"] == schema
    assert result["errors"][0]["schema"] == schema


def test_explain_unknown_schema_raises():
    with pytest.raises(m.UnknownSchemaError):
        m.explain("nope", 1)


def test_explain_invalid_schema_raises():
    with pytest.raises(TypeError):
        m.explain(123, 1)
