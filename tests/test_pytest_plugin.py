"""tests for the pytest plugin and assertion helpers."""

import textwrap

import pytest

from typsht import CheckerType, assert_no_errors, assert_type_equals, assert_type_error
from typsht._internal.pytest_plugin import (
    normalize_type,
    parse_inline_assertions,
    parse_output,
    parse_yaml_cases,
)


class TestNormalizeType:
    """tests for type string normalization."""

    def test_strips_builtins_prefix(self) -> None:
        assert normalize_type("builtins.int", CheckerType.MYPY) == "int"
        assert normalize_type("builtins.str", CheckerType.MYPY) == "str"

    def test_strips_nested_builtins(self) -> None:
        result = normalize_type("builtins.list[builtins.int]", CheckerType.MYPY)
        assert result == "list[int]"

    def test_normalizes_typing_generics(self) -> None:
        assert normalize_type("List[int]", CheckerType.PYRIGHT) == "list[int]"
        assert normalize_type("Dict[str, int]", CheckerType.PYRIGHT) == "dict[str, int]"
        assert normalize_type("Set[str]", CheckerType.PYRIGHT) == "set[str]"
        assert (
            normalize_type("Tuple[int, str]", CheckerType.PYRIGHT) == "tuple[int, str]"
        )

    def test_strips_typing_module(self) -> None:
        result = normalize_type("typing.List[int]", CheckerType.MYPY)
        assert result == "list[int]"


class TestParseOutput:
    """tests for output parsing."""

    def test_parse_mypy_reveal(self) -> None:
        output = '/tmp/test.py:2: note: Revealed type is "builtins.int"'
        result = parse_output(output, CheckerType.MYPY)

        assert result.revealed_types == {2: "int"}
        assert result.errors == []

    def test_parse_mypy_error(self) -> None:
        output = "/tmp/test.py:2: error: Incompatible return type  [return-value]"
        result = parse_output(output, CheckerType.MYPY)

        assert result.revealed_types == {}
        assert len(result.errors) == 1
        assert result.errors[0][0] == 2  # line
        assert result.errors[0][1] == "return-value"  # code
        assert "Incompatible return type" in result.errors[0][2]  # message

    def test_parse_pyright_reveal(self) -> None:
        output = '/tmp/test.py:2:13 - information: Type of "x" is "int"'
        result = parse_output(output, CheckerType.PYRIGHT)

        assert result.revealed_types == {2: "int"}

    def test_parse_pyright_error(self) -> None:
        output = '/tmp/test.py:2:12 - error: Type "int" is not assignable to return type "str"'
        result = parse_output(output, CheckerType.PYRIGHT)

        assert len(result.errors) == 1
        assert result.errors[0][0] == 2

    def test_parse_ty_reveal(self) -> None:
        output = textwrap.dedent("""\
            info[revealed-type]: Revealed type
             --> /tmp/test.py:2:13
              |
            2 | reveal_type(x)
              |             ^ `int`
              |
        """)
        result = parse_output(output, CheckerType.TY)

        assert result.revealed_types == {2: "int"}

    def test_parse_ty_error(self) -> None:
        output = textwrap.dedent("""\
            error[invalid-return-type]: Return type does not match
             --> /tmp/test.py:2:12
              |
        """)
        result = parse_output(output, CheckerType.TY)

        assert len(result.errors) == 1
        assert result.errors[0][0] == 2
        assert result.errors[0][1] == "invalid-return-type"


class TestAssertTypeEquals:
    """tests for assert_type_equals helper."""

    def test_simple_type(self) -> None:
        code = textwrap.dedent("""\
            x: int = 1
            reveal_type(x)
        """)
        # mypy only to keep test fast
        assert_type_equals(
            code, line=2, expected_type="int", checkers=[CheckerType.MYPY]
        )

    def test_list_type(self) -> None:
        code = textwrap.dedent("""\
            x: list[int] = [1, 2, 3]
            reveal_type(x)
        """)
        assert_type_equals(
            code, line=2, expected_type="list[int]", checkers=[CheckerType.MYPY]
        )

    def test_wrong_type_raises(self) -> None:
        code = textwrap.dedent("""\
            x: int = 1
            reveal_type(x)
        """)
        with pytest.raises(AssertionError, match="type mismatch"):
            assert_type_equals(
                code, line=2, expected_type="str", checkers=[CheckerType.MYPY]
            )

    def test_no_reveal_on_line_raises(self) -> None:
        code = textwrap.dedent("""\
            x: int = 1
        """)
        with pytest.raises(AssertionError, match="no revealed type"):
            assert_type_equals(
                code, line=1, expected_type="int", checkers=[CheckerType.MYPY]
            )


class TestAssertTypeError:
    """tests for assert_type_error helper."""

    def test_catches_return_type_error(self) -> None:
        code = textwrap.dedent("""\
            def foo(x: int) -> str:
                return x
        """)
        assert_type_error(code, checkers=[CheckerType.MYPY])

    def test_catches_error_on_specific_line(self) -> None:
        code = textwrap.dedent("""\
            def foo(x: int) -> str:
                return x
        """)
        assert_type_error(code, line=2, checkers=[CheckerType.MYPY])

    def test_matches_error_pattern(self) -> None:
        code = textwrap.dedent("""\
            def foo(x: int) -> str:
                return x
        """)
        assert_type_error(
            code, error_pattern="incompatible return", checkers=[CheckerType.MYPY]
        )

    def test_raises_when_no_error(self) -> None:
        code = textwrap.dedent("""\
            def foo(x: int) -> int:
                return x
        """)
        with pytest.raises(AssertionError, match="expected error but check passed"):
            assert_type_error(code, checkers=[CheckerType.MYPY])

    def test_raises_when_error_on_wrong_line(self) -> None:
        code = textwrap.dedent("""\
            def foo(x: int) -> str:
                return x
        """)
        with pytest.raises(AssertionError, match="no error on line"):
            assert_type_error(code, line=1, checkers=[CheckerType.MYPY])


class TestAssertNoErrors:
    """tests for assert_no_errors helper."""

    def test_valid_code_passes(self) -> None:
        code = textwrap.dedent("""\
            def foo(x: int) -> int:
                return x
        """)
        assert_no_errors(code, checkers=[CheckerType.MYPY])

    def test_invalid_code_raises(self) -> None:
        code = textwrap.dedent("""\
            def foo(x: int) -> str:
                return x
        """)
        with pytest.raises(AssertionError, match="unexpected errors"):
            assert_no_errors(code, checkers=[CheckerType.MYPY])


class TestParseYamlCases:
    """tests for YAML case parsing."""

    def test_parse_simple_case(self, tmp_path) -> None:
        yaml_content = textwrap.dedent("""\
            - case: test_simple
              main: |
                x: int = 1
                reveal_type(x)
              out: 'Revealed type is "builtins.int"'
        """)
        yaml_file = tmp_path / "test_cases.yml"
        yaml_file.write_text(yaml_content)

        cases = parse_yaml_cases(yaml_file)

        assert len(cases) == 1
        assert cases[0].name == "test_simple"
        assert "x: int = 1" in cases[0].main
        assert cases[0].expected_output == 'Revealed type is "builtins.int"'
        assert cases[0].regex is False

    def test_parse_regex_case(self, tmp_path) -> None:
        yaml_content = textwrap.dedent("""\
            - case: test_regex
              main: |
                reveal_type(x)
              out: 'Revealed type is ".*"'
              regex: yes
        """)
        yaml_file = tmp_path / "test_cases.yml"
        yaml_file.write_text(yaml_content)

        cases = parse_yaml_cases(yaml_file)

        assert len(cases) == 1
        assert cases[0].regex is True

    def test_parse_multi_checker(self, tmp_path) -> None:
        yaml_content = textwrap.dedent("""\
            - case: test_multi
              main: |
                x: int = 1
              checkers: [mypy, pyright]
        """)
        yaml_file = tmp_path / "test_cases.yml"
        yaml_file.write_text(yaml_content)

        cases = parse_yaml_cases(yaml_file)

        assert len(cases) == 1
        assert CheckerType.MYPY in cases[0].checkers
        assert CheckerType.PYRIGHT in cases[0].checkers

    def test_parse_should_pass(self, tmp_path) -> None:
        yaml_content = textwrap.dedent("""\
            - case: test_should_pass
              main: |
                x: int = 1
              should_pass: true
        """)
        yaml_file = tmp_path / "test_cases.yml"
        yaml_file.write_text(yaml_content)

        cases = parse_yaml_cases(yaml_file)

        assert len(cases) == 1
        assert cases[0].should_pass is True

    def test_parse_per_checker_output(self, tmp_path) -> None:
        yaml_content = textwrap.dedent("""\
            - case: test_per_checker
              main: |
                reveal_type(x)
              out_mypy: 'mypy output'
              out_pyright: 'pyright output'
        """)
        yaml_file = tmp_path / "test_cases.yml"
        yaml_file.write_text(yaml_content)

        cases = parse_yaml_cases(yaml_file)

        assert len(cases) == 1
        assert cases[0].checker_outputs[CheckerType.MYPY] == "mypy output"
        assert cases[0].checker_outputs[CheckerType.PYRIGHT] == "pyright output"

    def test_skips_invalid_items(self, tmp_path) -> None:
        yaml_content = textwrap.dedent("""\
            - case: valid_case
              main: |
                x: int = 1
            - not_a_dict
            - case: missing_main
        """)
        yaml_file = tmp_path / "test_cases.yml"
        yaml_file.write_text(yaml_content)

        cases = parse_yaml_cases(yaml_file)

        assert len(cases) == 1
        assert cases[0].name == "valid_case"

    def test_parse_inline_assertions(self, tmp_path) -> None:
        yaml_content = textwrap.dedent("""\
            - case: test_inline
              main: |
                x: int = 1
                reveal_type(x)  # R: int
        """)
        yaml_file = tmp_path / "test_cases.yml"
        yaml_file.write_text(yaml_content)

        cases = parse_yaml_cases(yaml_file)

        assert len(cases) == 1
        assert len(cases[0].inline_assertions) == 1
        assert cases[0].inline_assertions[0].line == 2
        assert cases[0].inline_assertions[0].kind == "R"
        assert cases[0].inline_assertions[0].pattern == "int"


class TestInlineAssertions:
    """tests for inline assertion parsing."""

    def test_parse_reveal_type_assertion(self) -> None:
        code = "reveal_type(x)  # R: int"
        assertions = parse_inline_assertions(code)

        assert len(assertions) == 1
        assert assertions[0].line == 1
        assert assertions[0].kind == "R"
        assert assertions[0].pattern == "int"

    def test_parse_error_assertion(self) -> None:
        code = "return x  # E: incompatible"
        assertions = parse_inline_assertions(code)

        assert len(assertions) == 1
        assert assertions[0].line == 1
        assert assertions[0].kind == "E"
        assert assertions[0].pattern == "incompatible"

    def test_parse_error_assertion_no_pattern(self) -> None:
        code = "return x  # E:"
        assertions = parse_inline_assertions(code)

        assert len(assertions) == 1
        assert assertions[0].kind == "E"
        assert assertions[0].pattern == ""

    def test_parse_multiple_assertions(self) -> None:
        code = textwrap.dedent("""\
            x: int = 1
            reveal_type(x)  # R: int
            def foo() -> str:
                return 1  # E: return
        """)
        assertions = parse_inline_assertions(code)

        assert len(assertions) == 2
        assert assertions[0].line == 2
        assert assertions[0].kind == "R"
        assert assertions[1].line == 4
        assert assertions[1].kind == "E"

    def test_parse_complex_type(self) -> None:
        code = "reveal_type(x)  # R: dict[str, list[int]]"
        assertions = parse_inline_assertions(code)

        assert len(assertions) == 1
        assert assertions[0].pattern == "dict[str, list[int]]"


class TestLiteralNormalization:
    """tests for Literal type normalization."""

    def test_literal_int_normalized(self) -> None:
        assert normalize_type("Literal[42]", CheckerType.PYRIGHT) == "int"
        assert normalize_type("Literal[-1]", CheckerType.PYRIGHT) == "int"

    def test_literal_str_normalized(self) -> None:
        assert normalize_type('Literal["foo"]', CheckerType.PYRIGHT) == "str"
        assert normalize_type("Literal['bar']", CheckerType.PYRIGHT) == "str"

    def test_literal_bool_normalized(self) -> None:
        assert normalize_type("Literal[True]", CheckerType.PYRIGHT) == "bool"
        assert normalize_type("Literal[False]", CheckerType.PYRIGHT) == "bool"

    def test_complex_literal_not_normalized(self) -> None:
        # union of literals should not be normalized
        result = normalize_type("Literal[1, 2, 3]", CheckerType.PYRIGHT)
        assert result == "Literal[1, 2, 3]"
