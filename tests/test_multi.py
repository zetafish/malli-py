import pytest

import malli as m


Shape = ["multi", {"dispatch": "type"},
         ["circle", ["map", ["type", "string"], ["radius", "int"]]],
         ["square", ["map", ["type", "string"], ["side", "int"]]]]


class TestBasic:
    def test_circle_valid(self):
        assert m.validate(Shape, {"type": "circle", "radius": 5}) is True

    def test_square_valid(self):
        assert m.validate(Shape, {"type": "square", "side": 3}) is True

    def test_wrong_shape_for_branch(self):
        assert m.validate(Shape, {"type": "circle", "side": 3}) is False

    def test_unknown_dispatch_value(self):
        assert m.validate(Shape, {"type": "triangle"}) is False

    def test_missing_dispatch_key(self):
        assert m.validate(Shape, {"radius": 5}) is False

    def test_non_dict(self):
        assert m.validate(Shape, "nope") is False


class TestSchemaValidation:
    def test_missing_dispatch_prop_raises(self):
        with pytest.raises(TypeError):
            m.validate(["multi", ["a", "int"]], {})

    def test_non_string_dispatch_raises(self):
        with pytest.raises(TypeError):
            m.validate(["multi", {"dispatch": 5}, ["a", "int"]], {})

    def test_no_branches_raises(self):
        with pytest.raises(TypeError):
            m.validate(["multi", {"dispatch": "t"}], {})

    def test_bad_branch_shape_raises(self):
        with pytest.raises(TypeError):
            m.validate(["multi", {"dispatch": "t"}, "not-a-branch"], {})

    def test_duplicate_branch_raises(self):
        with pytest.raises(TypeError):
            m.validate(
                ["multi", {"dispatch": "t"},
                 ["a", ["map", ["t", "string"]]],
                 ["a", ["map", ["t", "string"]]]],
                {},
            )


class TestExplain:
    def test_valid_returns_none(self):
        assert m.explain(Shape, {"type": "circle", "radius": 5}) is None

    def test_missing_dispatch(self):
        result = m.explain(Shape, {"radius": 5})
        errs = result["errors"]
        assert len(errs) == 1
        assert errs[0]["path"] == ["type"]
        assert errs[0]["type"] == "missing-dispatch"

    def test_invalid_dispatch(self):
        result = m.explain(Shape, {"type": "triangle"})
        errs = result["errors"]
        assert len(errs) == 1
        assert errs[0]["path"] == ["type"]
        assert errs[0]["value"] == "triangle"
        assert errs[0]["type"] == "invalid-dispatch"

    def test_branch_errors_bubble_up(self):
        # Dispatches to circle, but radius is wrong type — the branch's map validation runs.
        result = m.explain(Shape, {"type": "circle", "radius": "big"})
        errs = result["errors"]
        assert any(e["path"] == ["radius"] and e["value"] == "big" for e in errs)

    def test_non_dict_error(self):
        result = m.explain(Shape, "nope")
        assert result["errors"][0]["value"] == "nope"


class TestHumanize:
    def test_missing_dispatch(self):
        result = m.humanize(m.explain(Shape, {"radius": 5}))
        assert result == {"type": "missing dispatch key"}

    def test_invalid_dispatch(self):
        result = m.humanize(m.explain(Shape, {"type": "triangle"}))
        assert result == {"type": "unknown dispatch value 'triangle'"}

    def test_branch_error(self):
        result = m.humanize(m.explain(Shape, {"type": "circle", "radius": "big"}))
        assert result.get("radius") == "should be an int"

    def test_non_dict(self):
        result = m.humanize(m.explain(Shape, "nope"))
        assert result == {"": "should be a map"}


class TestDecode:
    def test_coerces_branch(self):
        result = m.decode(Shape, {"type": "circle", "radius": "5"}, m.string_transformer)
        assert result == {"type": "circle", "radius": 5}

    def test_no_dispatch_left_alone(self):
        result = m.decode(Shape, {"radius": "5"}, m.string_transformer)
        assert result == {"radius": "5"}

    def test_unknown_dispatch_left_alone(self):
        result = m.decode(Shape, {"type": "triangle", "n": "3"}, m.string_transformer)
        assert result == {"type": "triangle", "n": "3"}

    def test_non_dict_left_alone(self):
        assert m.decode(Shape, "nope", m.string_transformer) == "nope"


class TestNesting:
    def test_multi_inside_vector(self):
        schema = ["vector", Shape]
        value = [{"type": "circle", "radius": 1}, {"type": "square", "side": 2}]
        assert m.validate(schema, value) is True

    def test_multi_inside_map(self):
        schema = ["map", ["shape", Shape]]
        assert m.validate(schema, {"shape": {"type": "circle", "radius": 1}}) is True

    def test_parse_valid(self):
        assert m.parse(Shape, {"type": "circle", "radius": "5"}, m.string_transformer) == {
            "type": "circle",
            "radius": 5,
        }

    def test_parse_invalid(self):
        assert m.parse(Shape, {"type": "triangle"}, m.string_transformer) is m.INVALID
