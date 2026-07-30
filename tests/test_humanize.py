import pytest

import malli as m


class TestPassthrough:
    def test_none_in_none_out(self):
        assert m.humanize(None) is None

    def test_valid_input(self):
        assert m.humanize(m.explain("int", 3)) is None


class TestScalarMessages:
    def test_int(self):
        assert m.humanize(m.explain("int", "x")) == {"": "should be an int"}

    def test_int_bounds_both(self):
        assert m.humanize(m.explain(["int", {"min": 0, "max": 10}], -1)) == {
            "": "should be an int between 0 and 10"
        }

    def test_int_min_only(self):
        assert m.humanize(m.explain(["int", {"min": 0}], -1)) == {
            "": "should be an int at least 0"
        }

    def test_int_max_only(self):
        assert m.humanize(m.explain(["int", {"max": 10}], 11)) == {
            "": "should be an int at most 10"
        }

    def test_float(self):
        assert m.humanize(m.explain("float", 1)) == {"": "should be a float"}

    def test_string(self):
        assert m.humanize(m.explain("string", 1)) == {"": "should be a string"}

    def test_string_length(self):
        assert m.humanize(m.explain(["string", {"min": 2}], "a")) == {
            "": "should be a string at least 2 characters long"
        }

    def test_bool(self):
        assert m.humanize(m.explain("bool", 1)) == {"": "should be a boolean"}

    def test_nil(self):
        assert m.humanize(m.explain("nil", 0)) == {"": "should be nil"}

    def test_some(self):
        assert m.humanize(m.explain("some", None)) == {"": "should not be nil"}

    def test_uuid(self):
        assert m.humanize(m.explain("uuid", "x")) == {"": "should be a UUID"}

    def test_re(self):
        assert m.humanize(m.explain(["re", r"^\d+$"], "abc")) == {
            "": r"should match pattern ^\d+$"
        }


class TestEnumAndNot:
    def test_enum(self):
        result = m.humanize(m.explain(["enum", "a", "b"], "c"))
        assert result == {"": "should be one of 'a', 'b'"}

    def test_not(self):
        result = m.humanize(m.explain(["not", "int"], 3))
        assert result == {"": "should not match 'int'"}


class TestMap:
    User = [
        "map",
        ["name", "string"],
        ["age", ["int", {"min": 0}]],
        ["nickname", {"optional": True}, "string"],
    ]

    def test_missing_key(self):
        result = m.humanize(m.explain(self.User, {"age": 1}))
        assert result == {"name": "missing required key"}

    def test_invalid_value(self):
        result = m.humanize(m.explain(self.User, {"name": "Ada", "age": -1}))
        assert result == {"age": "should be an int at least 0"}

    def test_multiple(self):
        result = m.humanize(m.explain(self.User, {"age": -1}))
        assert result == {
            "name": "missing required key",
            "age": "should be an int at least 0",
        }

    def test_extra_key_on_closed(self):
        Closed = ["map", {"closed": True}, ["name", "string"]]
        result = m.humanize(m.explain(Closed, {"name": "Ada", "x": 1}))
        assert result == {"x": "should not be present"}

    def test_optional_invalid(self):
        result = m.humanize(m.explain(self.User, {"name": "Ada", "age": 1, "nickname": 3}))
        assert result == {"nickname": "should be a string"}


class TestCollectionTypeMismatch:
    def test_vector(self):
        assert m.humanize(m.explain(["vector", "int"], "abc")) == {"": "should be a vector"}

    def test_set(self):
        assert m.humanize(m.explain(["set", "int"], [1])) == {"": "should be a set"}

    def test_map(self):
        assert m.humanize(m.explain(["map", ["a", "int"]], "not-dict")) == {"": "should be a map"}

    def test_tuple_length(self):
        assert m.humanize(m.explain(["tuple", "int", "string"], [1])) == {
            "": "should be a tuple of 2 element(s)"
        }


class TestPathFormatting:
    def test_root(self):
        assert m.humanize(m.explain("int", "x")) == {"": "should be an int"}

    def test_map_key(self):
        result = m.humanize(m.explain(["map", ["a", "int"]], {"a": "x"}))
        assert result == {"a": "should be an int"}

    def test_vector_index(self):
        result = m.humanize(m.explain(["vector", "int"], [1, "x", 3]))
        assert result == {"[1]": "should be an int"}

    def test_mixed_path(self):
        schema = ["map", ["users", ["vector", ["map", ["name", "string"]]]]]
        value = {"users": [{"name": "Ada"}, {"name": 3}]}
        assert m.humanize(m.explain(schema, value)) == {"users[1].name": "should be a string"}

    def test_deep_indices(self):
        result = m.humanize(m.explain(["vector", ["vector", "int"]], [[1, 2], [3, "x"]]))
        assert result == {"[1][1]": "should be an int"}


class TestKeyCollision:
    def test_or_joins_with_and(self):
        result = m.humanize(m.explain(["or", "int", "string"], True))
        assert result == {"": "should be an int and should be a string"}


class TestUnknownSchemaFallback:
    def test_no_raise(self):
        # An error whose schema name isn't in _MESSAGES falls back gracefully.
        # Register a custom scalar and check its error uses "invalid".
        m.register("weird-scalar", lambda v, _p: False)
        result = m.humanize(m.explain("weird-scalar", 1))
        assert result == {"": "invalid"}
