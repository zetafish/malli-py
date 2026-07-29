import pytest

import malli as m


class TestVector:
    def test_valid(self):
        assert m.validate(["vector", "int"], [1, 2, 3]) is True

    def test_empty_ok(self):
        assert m.validate(["vector", "int"], []) is True

    @pytest.mark.parametrize("bad", ["abc", (1, 2), {1, 2}, {"a": 1}, 5, None])
    def test_non_list_rejected(self, bad):
        assert m.validate(["vector", "int"], bad) is False

    def test_element_mismatch(self):
        assert m.validate(["vector", "int"], [1, "x", 3]) is False

    def test_size_min(self):
        assert m.validate(["vector", {"min": 1}, "int"], []) is False
        assert m.validate(["vector", {"min": 1}, "int"], [1]) is True

    def test_size_max(self):
        assert m.validate(["vector", {"max": 2}, "int"], [1, 2, 3]) is False
        assert m.validate(["vector", {"max": 2}, "int"], [1, 2]) is True

    def test_explain_none_on_valid(self):
        assert m.explain(["vector", "int"], [1, 2]) is None

    def test_explain_element_path_and_in(self):
        result = m.explain(["vector", "int"], [1, "x", 3, "y"])
        assert result is not None
        errs = result["errors"]
        assert len(errs) == 2
        assert errs[0] == {"path": [0], "in": [1], "schema": "int", "value": "x"}
        assert errs[1] == {"path": [0], "in": [3], "schema": "int", "value": "y"}

    def test_explain_type_mismatch_is_collection_level(self):
        result = m.explain(["vector", "int"], "abc")
        err = result["errors"][0]
        assert err["path"] == []
        assert err["in"] == []
        assert err["schema"] == ["vector", "int"]
        assert err["value"] == "abc"

    def test_explain_size_bound_is_collection_level(self):
        result = m.explain(["vector", {"min": 1}, "int"], [])
        err = result["errors"][0]
        assert err["path"] == []
        assert err["in"] == []
        assert err["schema"] == ["vector", {"min": 1}, "int"]

    def test_nested_vector_paths_stack(self):
        result = m.explain(["vector", ["vector", "int"]], [[1, 2], [3, "x"]])
        err = result["errors"][0]
        assert err["path"] == [0, 0]
        assert err["in"] == [1, 1]
        assert err["value"] == "x"


class TestSequential:
    @pytest.mark.parametrize("v", [[1, 2], (1, 2), [], ()])
    def test_accepts_list_and_tuple(self, v):
        assert m.validate(["sequential", "int"], v) is True

    @pytest.mark.parametrize("v", ["abc", b"abc", {"a": 1}, {1, 2}, 5, None])
    def test_rejects_others(self, v):
        assert m.validate(["sequential", "int"], v) is False

    def test_element_mismatch(self):
        assert m.validate(["sequential", "int"], (1, "x")) is False

    def test_explain_element_path(self):
        result = m.explain(["sequential", "int"], (1, "x"))
        err = result["errors"][0]
        assert err["path"] == [0]
        assert err["in"] == [1]


class TestSet:
    def test_accepts_set(self):
        assert m.validate(["set", "int"], {1, 2, 3}) is True

    def test_accepts_frozenset(self):
        assert m.validate(["set", "int"], frozenset({1, 2})) is True

    @pytest.mark.parametrize("bad", [[1, 2], (1, 2), {"a": 1}, "abc"])
    def test_rejects_others(self, bad):
        assert m.validate(["set", "int"], bad) is False

    def test_element_mismatch(self):
        assert m.validate(["set", "int"], {1, "x"}) is False

    def test_explain_uses_element_for_in(self):
        result = m.explain(["set", "int"], {"x"})
        err = result["errors"][0]
        assert err["path"] == [0]
        assert err["in"] == ["x"]

    def test_size_bounds(self):
        assert m.validate(["set", {"min": 2}, "int"], {1}) is False
        assert m.validate(["set", {"max": 1}, "int"], {1, 2}) is False


class TestTuple:
    def test_positional_match(self):
        assert m.validate(["tuple", "int", "string"], [1, "x"]) is True
        assert m.validate(["tuple", "int", "string"], (1, "x")) is True

    def test_positional_mismatch(self):
        assert m.validate(["tuple", "int", "string"], ["x", 1]) is False

    def test_length_must_match(self):
        assert m.validate(["tuple", "int", "string"], [1]) is False
        assert m.validate(["tuple", "int", "string"], [1, "x", 3]) is False

    def test_empty_tuple(self):
        assert m.validate(["tuple"], []) is True
        assert m.validate(["tuple"], ()) is True
        assert m.validate(["tuple"], [1]) is False

    def test_non_seq_rejected(self):
        assert m.validate(["tuple", "int"], {1}) is False
        assert m.validate(["tuple", "int"], "1") is False

    def test_explain_length_mismatch_is_collection_level(self):
        result = m.explain(["tuple", "int", "string"], [1])
        err = result["errors"][0]
        assert err["path"] == []
        assert err["in"] == []
        assert err["schema"] == ["tuple", "int", "string"]

    def test_explain_positional_paths(self):
        result = m.explain(["tuple", "int", "string"], ["x", 1])
        errs = result["errors"]
        assert len(errs) == 2
        assert errs[0] == {"path": [0], "in": [0], "schema": "int", "value": "x"}
        assert errs[1] == {"path": [1], "in": [1], "schema": "string", "value": 1}

    def test_nested_in_vector(self):
        result = m.explain(["vector", ["tuple", "int", "string"]], [[1, "a"], [2, 3]])
        err = result["errors"][0]
        assert err["path"] == [0, 1]
        assert err["in"] == [1, 1]
        assert err["value"] == 3


class TestMapOf:
    def test_valid(self):
        assert m.validate(["map-of", "string", "int"], {"a": 1, "b": 2}) is True

    def test_empty_ok(self):
        assert m.validate(["map-of", "string", "int"], {}) is True

    @pytest.mark.parametrize("bad", [[("a", 1)], "a", None, {1, 2}])
    def test_non_dict_rejected(self, bad):
        assert m.validate(["map-of", "string", "int"], bad) is False

    def test_bad_value(self):
        assert m.validate(["map-of", "string", "int"], {"a": "x"}) is False

    def test_bad_key(self):
        assert m.validate(["map-of", "string", "int"], {1: 1}) is False

    def test_explain_bad_value_path(self):
        result = m.explain(["map-of", "string", "int"], {"a": "x"})
        err = result["errors"][0]
        assert err["path"] == [1]
        assert err["in"] == ["a"]
        assert err["value"] == "x"

    def test_explain_bad_key_path(self):
        result = m.explain(["map-of", "string", "int"], {1: 1})
        err = result["errors"][0]
        assert err["path"] == [0]
        assert err["in"] == [1]
        assert err["value"] == 1

    def test_size_bounds(self):
        assert m.validate(["map-of", {"min": 1}, "string", "int"], {}) is False
        assert m.validate(["map-of", {"max": 1}, "string", "int"], {"a": 1, "b": 2}) is False


class TestArityErrors:
    def test_vector_no_child(self):
        with pytest.raises(TypeError):
            m.validate(["vector"], [])

    def test_vector_two_children(self):
        with pytest.raises(TypeError):
            m.validate(["vector", "int", "string"], [])

    def test_set_no_child(self):
        with pytest.raises(TypeError):
            m.validate(["set"], set())

    def test_map_of_one_child(self):
        with pytest.raises(TypeError):
            m.validate(["map-of", "string"], {})

    def test_map_of_three_children(self):
        with pytest.raises(TypeError):
            m.validate(["map-of", "string", "int", "int"], {})


class TestCompositionWithCollections:
    def test_vector_of_or(self):
        schema = ["vector", ["or", "int", "string"]]
        assert m.validate(schema, [1, "x", 2]) is True
        assert m.validate(schema, [1, True]) is False

    def test_and_of_vectors(self):
        schema = ["and", ["vector", "int"], ["vector", {"min": 1}, "any"]]
        assert m.validate(schema, [1, 2]) is True
        assert m.validate(schema, []) is False
        assert m.validate(schema, [1, "x"]) is False

    def test_maybe_vector(self):
        assert m.validate(["maybe", ["vector", "int"]], None) is True
        assert m.validate(["maybe", ["vector", "int"]], [1, 2]) is True
        assert m.validate(["maybe", ["vector", "int"]], [1, "x"]) is False
