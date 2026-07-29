import pytest

import malli as m


User = [
    "map",
    ["name", "string"],
    ["age", ["int", {"min": 0}]],
    ["nickname", {"optional": True}, "string"],
]


class TestBasic:
    def test_valid(self):
        assert m.validate(User, {"name": "Ada", "age": 42}) is True

    def test_valid_with_optional(self):
        assert m.validate(User, {"name": "Ada", "age": 42, "nickname": "A"}) is True

    def test_open_extra_keys_ok(self):
        assert m.validate(User, {"name": "Ada", "age": 42, "extra": 1}) is True

    def test_missing_required(self):
        assert m.validate(User, {"name": "Ada"}) is False

    def test_invalid_value(self):
        assert m.validate(User, {"name": "Ada", "age": -1}) is False

    def test_invalid_optional(self):
        assert m.validate(User, {"name": "Ada", "age": 1, "nickname": 3}) is False

    @pytest.mark.parametrize("bad", [None, [], "x", 5, {1, 2}])
    def test_non_dict(self, bad):
        assert m.validate(User, bad) is False


class TestClosed:
    Closed = ["map", {"closed": True}, ["name", "string"]]

    def test_ok_when_only_known_keys(self):
        assert m.validate(self.Closed, {"name": "Ada"}) is True

    def test_extra_key_rejected(self):
        assert m.validate(self.Closed, {"name": "Ada", "extra": 1}) is False

    def test_all_optional_closed_empty_ok(self):
        schema = ["map", {"closed": True}, ["x", {"optional": True}, "int"]]
        assert m.validate(schema, {}) is True
        assert m.validate(schema, {"x": 1}) is True
        assert m.validate(schema, {"y": 1}) is False


class TestExplain:
    def test_none_when_valid(self):
        assert m.explain(User, {"name": "Ada", "age": 42}) is None

    def test_missing_key_error(self):
        result = m.explain(User, {"name": "Ada"})
        assert result is not None
        errs = result["errors"]
        assert len(errs) == 1
        assert errs[0] == {
            "path": ["age"],
            "in": ["age"],
            "schema": ["int", {"min": 0}],
            "value": None,
            "type": "missing-key",
        }

    def test_invalid_value_error(self):
        result = m.explain(User, {"name": "Ada", "age": -1})
        errs = result["errors"]
        assert len(errs) == 1
        assert errs[0]["path"] == ["age"]
        assert errs[0]["in"] == ["age"]
        assert errs[0]["value"] == -1
        assert "type" not in errs[0]

    def test_multiple_errors(self):
        result = m.explain(User, {"age": -1})
        errs = result["errors"]
        assert len(errs) == 2
        by_path = {tuple(e["path"]): e for e in errs}
        assert by_path[("name",)]["type"] == "missing-key"
        assert by_path[("age",)]["value"] == -1

    def test_non_dict_is_collection_level(self):
        result = m.explain(User, "not a dict")
        err = result["errors"][0]
        assert err["path"] == []
        assert err["in"] == []
        assert err["value"] == "not a dict"

    def test_open_extra_key_not_reported(self):
        assert m.explain(User, {"name": "Ada", "age": 1, "extra": 1}) is None

    def test_closed_extra_key_error(self):
        Closed = ["map", {"closed": True}, ["name", "string"]]
        result = m.explain(Closed, {"name": "Ada", "extra": 99})
        errs = result["errors"]
        assert len(errs) == 1
        assert errs[0] == {
            "path": ["extra"],
            "in": ["extra"],
            "schema": Closed,
            "value": 99,
            "type": "extra-key",
        }


class TestNesting:
    def test_nested_map(self):
        schema = ["map", ["user", ["map", ["name", "string"]]]]
        assert m.validate(schema, {"user": {"name": "Ada"}}) is True
        result = m.explain(schema, {"user": {"name": 3}})
        err = result["errors"][0]
        assert err["path"] == ["user", "name"]
        assert err["in"] == ["user", "name"]
        assert err["value"] == 3

    def test_map_in_vector(self):
        schema = ["vector", ["map", ["name", "string"]]]
        assert m.validate(schema, [{"name": "Ada"}, {"name": "Bob"}]) is True
        result = m.explain(schema, [{"name": "Ada"}, {"name": 3}])
        err = result["errors"][0]
        assert err["path"] == [0, "name"]
        assert err["in"] == [1, "name"]
        assert err["value"] == 3

    def test_vector_in_map(self):
        schema = ["map", ["tags", ["vector", "string"]]]
        result = m.explain(schema, {"tags": ["a", 1]})
        err = result["errors"][0]
        assert err["path"] == ["tags", 0]
        assert err["in"] == ["tags", 1]


class TestEntryParsing:
    def test_bad_entry_shape(self):
        with pytest.raises(TypeError):
            m.validate(["map", "name"], {})

    def test_too_many_elements(self):
        with pytest.raises(TypeError):
            m.validate(["map", ["a", "b", "c", "d"]], {})

    def test_non_string_key(self):
        with pytest.raises(TypeError):
            m.validate(["map", [1, "int"]], {})

    def test_duplicate_key(self):
        with pytest.raises(TypeError):
            m.validate(["map", ["a", "int"], ["a", "string"]], {"a": 1})

    def test_non_dict_props(self):
        with pytest.raises(TypeError):
            m.validate(["map", ["a", "not-props", "int"]], {"a": 1})


class TestComposition:
    def test_and_of_maps(self):
        schema = [
            "and",
            ["map", ["name", "string"]],
            ["map", ["age", "int"]],
        ]
        assert m.validate(schema, {"name": "Ada", "age": 1}) is True
        assert m.validate(schema, {"name": "Ada"}) is False

    def test_maybe_map(self):
        schema = ["maybe", ["map", ["name", "string"]]]
        assert m.validate(schema, None) is True
        assert m.validate(schema, {"name": "Ada"}) is True
        assert m.validate(schema, {"name": 3}) is False

    def test_or_map_or_string(self):
        schema = ["or", ["map", ["k", "int"]], "string"]
        assert m.validate(schema, {"k": 1}) is True
        assert m.validate(schema, "hi") is True
        assert m.validate(schema, {"k": "x"}) is False
