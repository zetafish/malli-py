import pytest

import malli as m


class TestAnd:
    def test_all_pass(self):
        assert m.validate(["and", "int", ["int", {"min": 0}]], 5) is True

    def test_one_fails(self):
        assert m.validate(["and", "int", ["int", {"min": 0}]], -1) is False

    def test_explain_collects_only_failing(self):
        result = m.explain(["and", "int", ["int", {"min": 0}]], -1)
        assert result is not None
        errs = result["errors"]
        assert len(errs) == 1
        assert errs[0]["path"] == [1]
        assert errs[0]["value"] == -1

    def test_explain_collects_all_failing(self):
        result = m.explain(["and", "int", ["int", {"min": 0}]], "x")
        assert result is not None
        errs = result["errors"]
        assert len(errs) == 2
        assert [e["path"] for e in errs] == [[0], [1]]

    def test_explain_none_when_valid(self):
        assert m.explain(["and", "int", ["int", {"min": 0}]], 5) is None


class TestOr:
    @pytest.mark.parametrize("v", [3, "hi"])
    def test_one_branch_passes(self, v):
        assert m.validate(["or", "int", "string"], v) is True

    def test_no_branch_passes(self):
        assert m.validate(["or", "int", "string"], True) is False

    def test_explain_reports_all_branches(self):
        result = m.explain(["or", "int", "string"], True)
        assert result is not None
        errs = result["errors"]
        assert len(errs) == 2
        assert [e["path"] for e in errs] == [[0], [1]]

    def test_explain_none_when_any_branch_passes(self):
        assert m.explain(["or", "int", "string"], 3) is None


class TestEnum:
    @pytest.mark.parametrize("v", ["red", "green", "blue"])
    def test_member_passes(self, v):
        assert m.validate(["enum", "red", "green", "blue"], v) is True

    def test_non_member_fails(self):
        assert m.validate(["enum", "red", "green"], "purple") is False

    def test_int_and_none_members(self):
        assert m.validate(["enum", 1, 2, None], None) is True
        assert m.validate(["enum", 1, 2, None], 3) is False

    def test_explain_carries_full_enum_schema(self):
        result = m.explain(["enum", "a", "b"], "c")
        assert result["errors"][0]["schema"] == ["enum", "a", "b"]


class TestMaybe:
    def test_none_passes(self):
        assert m.validate(["maybe", "int"], None) is True

    def test_child_validates(self):
        assert m.validate(["maybe", "int"], 3) is True
        assert m.validate(["maybe", "int"], "x") is False

    def test_explain_child_path(self):
        result = m.explain(["maybe", ["int", {"min": 0}]], -1)
        assert result is not None
        assert result["errors"][0]["path"] == [0]


class TestNot:
    def test_child_fails_means_pass(self):
        assert m.validate(["not", "int"], "x") is True

    def test_child_passes_means_fail(self):
        assert m.validate(["not", "int"], 3) is False

    def test_explain_carries_not_schema(self):
        result = m.explain(["not", "int"], 3)
        assert result["errors"][0]["schema"] == ["not", "int"]


class TestNesting:
    def test_and_or_not_composes(self):
        schema = ["and", ["or", "int", "string"], ["not", "nil"]]
        assert m.validate(schema, 3) is True
        assert m.validate(schema, "x") is True
        assert m.validate(schema, None) is False
        assert m.validate(schema, True) is False


class TestArityErrors:
    def test_maybe_too_many(self):
        with pytest.raises(TypeError):
            m.validate(["maybe", "int", "int"], 3)

    def test_not_zero(self):
        with pytest.raises(TypeError):
            m.validate(["not"], 3)

    def test_enum_empty(self):
        with pytest.raises(TypeError):
            m.validate(["enum"], 3)

    def test_and_empty(self):
        with pytest.raises(TypeError):
            m.validate(["and"], 3)


class TestPropsForm:
    def test_and_with_props_map(self):
        assert m.validate(["and", {}, "int", ["int", {"min": 0}]], 5) is True
        assert m.validate(["and", {}, "int", ["int", {"min": 0}]], -1) is False

    def test_or_with_props_map(self):
        assert m.validate(["or", {}, "int", "string"], "hi") is True


class TestExplainWrapper:
    def test_top_level_shape(self):
        result = m.explain(["and", "int"], "x")
        assert result["value"] == "x"
        assert result["schema"] == ["and", "int"]
        assert isinstance(result["errors"], list)
        assert len(result["errors"]) >= 1


class TestBackwardsCompat:
    def test_scalar_validate_still_works(self):
        assert m.validate("int", 3) is True
        assert m.validate(["int", {"min": 0}], -1) is False

    def test_scalar_explain_still_works(self):
        assert m.explain("int", 3) is None
        result = m.explain("int", "x")
        assert result["errors"][0]["path"] == []

    def test_re_raw_arg_still_works(self):
        assert m.validate(["re", r"^\d+$"], "42") is True
        assert m.validate(["re", r"^\d+$"], "abc") is False

    def test_re_props_form_still_works(self):
        assert m.validate(["re", {"pattern": r"^\d+$"}], "42") is True
