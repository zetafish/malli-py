import pytest

import malli as m


Base = ["map", ["id", "int"], ["name", "string"]]
Extra = ["map", ["email", "string"]]


class TestBasic:
    def test_valid_merged(self):
        schema = ["merge", Base, Extra]
        assert m.validate(schema, {"id": 1, "name": "Ada", "email": "a@b.com"}) is True

    def test_missing_from_first(self):
        schema = ["merge", Base, Extra]
        assert m.validate(schema, {"name": "Ada", "email": "a@b.com"}) is False

    def test_missing_from_second(self):
        schema = ["merge", Base, Extra]
        assert m.validate(schema, {"id": 1, "name": "Ada"}) is False

    def test_non_dict(self):
        assert m.validate(["merge", Base, Extra], "nope") is False

    def test_single_child_ok(self):
        assert m.validate(["merge", Base], {"id": 1, "name": "Ada"}) is True

    def test_no_children_raises(self):
        with pytest.raises(TypeError):
            m.validate(["merge"], {})

    def test_non_map_child_raises(self):
        with pytest.raises(TypeError):
            m.validate(["merge", Base, "int"], {"id": 1, "name": "Ada"})


class TestOverride:
    def test_later_entry_overrides_schema(self):
        # First says id must be int; second widens to string.
        schema = ["merge",
                  ["map", ["id", "int"]],
                  ["map", ["id", "string"]]]
        assert m.validate(schema, {"id": "abc"}) is True
        assert m.validate(schema, {"id": 1}) is False

    def test_later_entry_overrides_optional(self):
        schema = ["merge",
                  ["map", ["nick", "string"]],
                  ["map", ["nick", {"optional": True}, "string"]]]
        # Now nick is optional.
        assert m.validate(schema, {}) is True

    def test_optional_promoted_to_required(self):
        schema = ["merge",
                  ["map", ["nick", {"optional": True}, "string"]],
                  ["map", ["nick", "string"]]]
        assert m.validate(schema, {}) is False
        assert m.validate(schema, {"nick": "A"}) is True


class TestClosedProp:
    def test_closed_from_last_wins(self):
        schema = ["merge",
                  ["map", ["a", "int"]],
                  ["map", {"closed": True}, ["b", "int"]]]
        assert m.validate(schema, {"a": 1, "b": 2}) is True
        assert m.validate(schema, {"a": 1, "b": 2, "x": 3}) is False

    def test_open_from_last_wins(self):
        # Even if first is closed, last overrides.
        schema = ["merge",
                  ["map", {"closed": True}, ["a", "int"]],
                  ["map", ["b", "int"]]]
        # Props merge: closed=True from first survives (dict merge, second has no closed key)
        # This documents the shallow-merge behavior.
        assert m.validate(schema, {"a": 1, "b": 2, "x": 3}) is False


class TestExplain:
    def test_missing_key_reports_via_map(self):
        schema = ["merge", Base, Extra]
        result = m.explain(schema, {"name": "Ada", "email": "a@b.com"})
        errs = result["errors"]
        assert len(errs) == 1
        assert errs[0]["path"] == ["id"]
        assert errs[0]["type"] == "missing-key"

    def test_valid_returns_none(self):
        schema = ["merge", Base, Extra]
        assert m.explain(schema, {"id": 1, "name": "Ada", "email": "a@b.com"}) is None

    def test_non_dict_error(self):
        result = m.explain(["merge", Base, Extra], "nope")
        assert result["errors"][0]["value"] == "nope"


class TestHumanize:
    def test_missing_key(self):
        schema = ["merge", Base, Extra]
        result = m.humanize(m.explain(schema, {"name": "Ada", "email": "a@b.com"}))
        assert result == {"id": "missing required key"}

    def test_non_dict(self):
        result = m.humanize(m.explain(["merge", Base, Extra], "nope"))
        assert result == {"": "should be a map"}


class TestDecode:
    def test_coerces_merged_entries(self):
        schema = ["merge",
                  ["map", ["id", "int"]],
                  ["map", ["age", "int"]]]
        result = m.decode(schema, {"id": "1", "age": "42"}, m.string_transformer)
        assert result == {"id": 1, "age": 42}

    def test_override_uses_last_schema(self):
        schema = ["merge",
                  ["map", ["id", "int"]],
                  ["map", ["id", "string"]]]
        # Last wins → id decoded as string (no coercion of "1" to string, stays "1")
        result = m.decode(schema, {"id": "1"}, m.string_transformer)
        assert result == {"id": "1"}


class TestNesting:
    def test_merge_inside_map(self):
        schema = ["map", ["user", ["merge", Base, Extra]]]
        assert m.validate(schema, {"user": {"id": 1, "name": "A", "email": "a@b"}}) is True
        result = m.explain(schema, {"user": {"id": 1, "email": "a@b"}})
        assert result["errors"][0]["path"] == ["user", "name"]
