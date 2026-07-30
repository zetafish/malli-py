import uuid

import pytest

import malli as m


class TestStringTransformerScalars:
    def test_int(self):
        assert m.decode("int", "42", m.string_transformer) == 42

    def test_int_invalid_left_alone(self):
        assert m.decode("int", "abc", m.string_transformer) == "abc"

    def test_int_already_int(self):
        assert m.decode("int", 42, m.string_transformer) == 42

    def test_float(self):
        assert m.decode("float", "3.14", m.string_transformer) == 3.14

    def test_bool_true(self):
        assert m.decode("bool", "true", m.string_transformer) is True

    def test_bool_false(self):
        assert m.decode("bool", "FALSE", m.string_transformer) is False

    def test_bool_unknown_left_alone(self):
        assert m.decode("bool", "maybe", m.string_transformer) == "maybe"

    def test_uuid(self):
        s = "12345678-1234-5678-1234-567812345678"
        assert m.decode("uuid", s, m.string_transformer) == uuid.UUID(s)

    def test_uuid_bad_left_alone(self):
        assert m.decode("uuid", "not-a-uuid", m.string_transformer) == "not-a-uuid"

    def test_string_from_int(self):
        assert m.decode("string", 42, m.string_transformer) == "42"

    def test_string_already_string(self):
        assert m.decode("string", "hi", m.string_transformer) == "hi"


class TestNoOpForUnknownScalar:
    def test_any_untouched(self):
        assert m.decode("any", "42", m.string_transformer) == "42"


class TestCollections:
    def test_vector_of_ints(self):
        assert m.decode(["vector", "int"], ["1", "2", "3"], m.string_transformer) == [1, 2, 3]

    def test_vector_non_list_untouched(self):
        assert m.decode(["vector", "int"], "nope", m.string_transformer) == "nope"

    def test_sequential_list(self):
        assert m.decode(["sequential", "int"], ["1", "2"], m.string_transformer) == [1, 2]

    def test_sequential_tuple(self):
        assert m.decode(["sequential", "int"], ("1", "2"), m.string_transformer) == (1, 2)

    def test_tuple(self):
        assert m.decode(["tuple", "int", "string"], ["1", 2], m.string_transformer) == [1, "2"]

    def test_tuple_length_mismatch_untouched(self):
        assert m.decode(["tuple", "int", "string"], ["1"], m.string_transformer) == ["1"]

    def test_set_of_ints(self):
        assert m.decode(["set", "int"], {"1", "2"}, m.string_transformer) == {1, 2}

    def test_map_of(self):
        result = m.decode(["map-of", "string", "int"], {"a": "1", "b": "2"}, m.string_transformer)
        assert result == {"a": 1, "b": 2}

    def test_map_of_non_dict_untouched(self):
        assert m.decode(["map-of", "string", "int"], "nope", m.string_transformer) == "nope"


class TestMap:
    User = ["map", ["name", "string"], ["age", "int"], ["opt", {"optional": True}, "int"]]

    def test_basic(self):
        result = m.decode(self.User, {"name": "Ada", "age": "42"}, m.string_transformer)
        assert result == {"name": "Ada", "age": 42}

    def test_optional_present(self):
        result = m.decode(self.User, {"name": "Ada", "age": "1", "opt": "7"}, m.string_transformer)
        assert result == {"name": "Ada", "age": 1, "opt": 7}

    def test_optional_absent(self):
        result = m.decode(self.User, {"name": "Ada", "age": "1"}, m.string_transformer)
        assert result == {"name": "Ada", "age": 1}

    def test_extra_keys_kept(self):
        result = m.decode(self.User, {"name": "Ada", "age": "1", "x": "y"}, m.string_transformer)
        assert result == {"name": "Ada", "age": 1, "x": "y"}

    def test_non_dict_untouched(self):
        assert m.decode(self.User, "nope", m.string_transformer) == "nope"

    def test_nested(self):
        schema = ["map", ["user", self.User]]
        result = m.decode(schema, {"user": {"name": "Ada", "age": "3"}}, m.string_transformer)
        assert result == {"user": {"name": "Ada", "age": 3}}


class TestComposites:
    def test_maybe_none(self):
        assert m.decode(["maybe", "int"], None, m.string_transformer) is None

    def test_maybe_value(self):
        assert m.decode(["maybe", "int"], "42", m.string_transformer) == 42

    def test_and_chain(self):
        schema = ["and", "int", ["int", {"min": 0}]]
        assert m.decode(schema, "5", m.string_transformer) == 5

    def test_or_picks_first_valid(self):
        schema = ["or", "int", "string"]
        assert m.decode(schema, "42", m.string_transformer) == 42

    def test_or_falls_through(self):
        schema = ["or", "int", "string"]
        assert m.decode(schema, "abc", m.string_transformer) == "abc"

    def test_enum_untouched(self):
        assert m.decode(["enum", "a", "b"], "a", m.string_transformer) == "a"


class TestJsonTransformer:
    def test_set_from_list(self):
        assert m.decode(["set", "int"], [1, 2, 3], m.json_transformer) == {1, 2, 3}

    def test_tuple_from_list(self):
        assert m.decode(["tuple", "int", "string"], [1, "x"], m.json_transformer) == (1, "x")

    def test_uuid_from_string(self):
        s = "12345678-1234-5678-1234-567812345678"
        assert m.decode("uuid", s, m.json_transformer) == uuid.UUID(s)


class TestParse:
    def test_valid_returns_value(self):
        assert m.parse("int", 42) == 42

    def test_invalid_returns_sentinel(self):
        assert m.parse("int", "x") is m.INVALID

    def test_with_transformer_valid(self):
        assert m.parse("int", "42", m.string_transformer) == 42

    def test_with_transformer_invalid(self):
        assert m.parse("int", "abc", m.string_transformer) is m.INVALID

    def test_invalid_is_falsy(self):
        assert not m.INVALID

    def test_invalid_singleton(self):
        assert m.INVALID is m.INVALID

    def test_invalid_repr(self):
        assert repr(m.INVALID) == "INVALID"

    def test_parse_map_coerces(self):
        User = ["map", ["age", "int"]]
        assert m.parse(User, {"age": "42"}, m.string_transformer) == {"age": 42}


class TestNoMutation:
    def test_dict_not_mutated(self):
        original = {"age": "42"}
        result = m.decode(["map", ["age", "int"]], original, m.string_transformer)
        assert original == {"age": "42"}
        assert result == {"age": 42}

    def test_list_not_mutated(self):
        original = ["1", "2"]
        result = m.decode(["vector", "int"], original, m.string_transformer)
        assert original == ["1", "2"]
        assert result == [1, 2]
