"""pytest plugin for typsht - type checker agnostic test assertions.

this plugin enables running type checking tests across multiple type checkers
(mypy, pyright, ty) using YAML test case files compatible with pytest-mypy-plugins.

usage:
    # in pyproject.toml
    [project.entry-points.pytest11]
    typsht = "typsht._internal.pytest_plugin"

    # run tests
    pytest tests/typesafety/

yaml test case format:
    - case: test_name
      main: |
        from mylib import foo
        reveal_type(foo)
      out: "main:2: note: Revealed type is ..."
      regex: yes  # optional, for pattern matching
      checkers: [mypy, pyright]  # optional, defaults to mypy
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import yaml

from typsht._internal.checkers import get_checker
from typsht._internal.types import CheckerType, SourceInput

# ---------------------------------------------------------------------------
# test case types
# ---------------------------------------------------------------------------


@dataclass
class TypeTestCase:
    """a single type checking test case."""

    name: str
    main: str
    expected_output: str | None = None
    regex: bool = False
    should_pass: bool | None = None
    checkers: list[CheckerType] = field(default_factory=lambda: [CheckerType.MYPY])
    checker_outputs: dict[CheckerType, str] = field(default_factory=dict)
    source_path: Path | None = None  # path to yaml file for error reporting


@dataclass
class NormalizedOutput:
    """normalized type checker output for cross-checker comparison."""

    revealed_types: dict[int, str]  # line_number -> type
    errors: list[tuple[int, str, str]]  # (line, error_code, message)
    notes: list[tuple[int, str]]  # (line, message)
    raw: str


# ---------------------------------------------------------------------------
# output parsing
# ---------------------------------------------------------------------------

# mypy: /path/file.py:2: note: Revealed type is "builtins.int"
MYPY_REVEAL_PATTERN = re.compile(
    r"(?P<file>[^:]+):(?P<line>\d+): note: Revealed type is \"(?P<type>.+)\""
)

# pyright: /path/file.py:2:13 - information: Type of "x" is "Literal[1]"
PYRIGHT_REVEAL_PATTERN = re.compile(
    r"(?P<file>[^:]+):(?P<line>\d+):\d+ - information: Type of \"[^\"]+\" is \"(?P<type>.+)\""
)

# ty multiline format - need to capture the type from the ^ `type` line
# info[revealed-type]: Revealed type
#  --> /path/file.py:2:13
#   |
# 2 | reveal_type(x)
#   |             ^ `list[int]`
TY_REVEAL_PATTERN = re.compile(
    r"info\[revealed-type\]: Revealed type\n"
    r"\s*--> (?P<file>[^:]+):(?P<line>\d+):\d+\n"
    r".*?\n"
    r".*?\n"
    r"\s*\|\s*\^\s*`(?P<type>[^`]+)`",
    re.MULTILINE | re.DOTALL,
)

# error patterns
MYPY_ERROR_PATTERN = re.compile(
    r"(?P<file>[^:]+):(?P<line>\d+): error: (?P<msg>.+?)(?:\s+\[(?P<code>[\w-]+)\])?$",
    re.MULTILINE,
)

PYRIGHT_ERROR_PATTERN = re.compile(
    r"(?P<file>[^:]+):(?P<line>\d+):\d+ - error: (?P<msg>.+)",
    re.MULTILINE,
)

# ty error format:
# error[invalid-return-type]: Return type does not match returned value
#  --> /path/file.py:1:20
TY_ERROR_PATTERN = re.compile(
    r"error\[(?P<code>[\w-]+)\]: (?P<msg>.+)\n"
    r"\s*--> (?P<file>[^:]+):(?P<line>\d+):\d+",
    re.MULTILINE,
)


def normalize_type(type_str: str, checker: CheckerType) -> str:
    """normalize type representations across checkers.

    mypy:    builtins.int, builtins.str, builtins.list[builtins.int]
    pyright: int, str, List[int]
    ty:      int, str, list[int]

    we normalize to lowercase modern Python style: int, str, list[int]
    """
    result = type_str

    # strip builtins. prefix (mypy)
    result = re.sub(r"\bbuiltins\.", "", result)

    # strip typing. prefix
    result = re.sub(r"\btyping\.", "", result)

    # normalize old-style generics to new style (pyright uses capitals)
    result = re.sub(r"\bList\b", "list", result)
    result = re.sub(r"\bDict\b", "dict", result)
    result = re.sub(r"\bSet\b", "set", result)
    result = re.sub(r"\bTuple\b", "tuple", result)
    result = re.sub(r"\bFrozenSet\b", "frozenset", result)
    result = re.sub(r"\bType\b", "type", result)

    return result


def parse_output(output: str, checker: CheckerType) -> NormalizedOutput:
    """parse type checker output into normalized form."""
    revealed_types: dict[int, str] = {}
    errors: list[tuple[int, str, str]] = []
    notes: list[tuple[int, str]] = []

    if checker == CheckerType.MYPY:
        for m in MYPY_REVEAL_PATTERN.finditer(output):
            line_num = int(m.group("line"))
            type_str = normalize_type(m.group("type"), checker)
            revealed_types[line_num] = type_str

        for m in MYPY_ERROR_PATTERN.finditer(output):
            line_num = int(m.group("line"))
            code = m.group("code") or ""
            msg = m.group("msg")
            errors.append((line_num, code, msg))

    elif checker == CheckerType.PYRIGHT:
        for m in PYRIGHT_REVEAL_PATTERN.finditer(output):
            line_num = int(m.group("line"))
            type_str = normalize_type(m.group("type"), checker)
            revealed_types[line_num] = type_str

        for m in PYRIGHT_ERROR_PATTERN.finditer(output):
            line_num = int(m.group("line"))
            msg = m.group("msg")
            errors.append((line_num, "", msg))

    elif checker == CheckerType.TY:
        for m in TY_REVEAL_PATTERN.finditer(output):
            line_num = int(m.group("line"))
            type_str = normalize_type(m.group("type"), checker)
            revealed_types[line_num] = type_str

        for m in TY_ERROR_PATTERN.finditer(output):
            line_num = int(m.group("line"))
            code = m.group("code")
            msg = m.group("msg")
            errors.append((line_num, code, msg))

    return NormalizedOutput(
        revealed_types=revealed_types,
        errors=errors,
        notes=notes,
        raw=output,
    )


# ---------------------------------------------------------------------------
# yaml parsing
# ---------------------------------------------------------------------------


def parse_yaml_cases(path: Path) -> list[TypeTestCase]:
    """parse test cases from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, list):
        return []

    cases = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if "case" not in item or "main" not in item:
            continue

        # determine which checkers to run
        checkers_raw = item.get("checkers", ["mypy"])
        if isinstance(checkers_raw, str):
            checkers_raw = [checkers_raw]

        checkers = []
        for c in checkers_raw:
            with contextlib.suppress(ValueError):
                checkers.append(CheckerType(c))

        if not checkers:
            checkers = [CheckerType.MYPY]

        # parse per-checker outputs if provided
        checker_outputs: dict[CheckerType, str] = {}
        for checker in CheckerType:
            key = f"out_{checker.value}"
            if key in item:
                checker_outputs[checker] = item[key]

        # handle regex flag variations
        regex = item.get("regex", False)
        if isinstance(regex, str):
            regex = regex.lower() in ("yes", "true", "1")

        case = TypeTestCase(
            name=item["case"],
            main=item["main"],
            expected_output=item.get("out"),
            regex=regex,
            should_pass=item.get("should_pass"),
            checkers=checkers,
            checker_outputs=checker_outputs,
            source_path=path,
        )
        cases.append(case)

    return cases


# ---------------------------------------------------------------------------
# pytest hooks and classes
# ---------------------------------------------------------------------------


class TypeTestFailure(Exception):
    """raised when a type test fails."""


def pytest_collect_file(
    parent: pytest.Collector, file_path: Path
) -> TypeTestFile | None:
    """collect type test files."""
    if file_path.suffix not in (".yml", ".yaml"):
        return None
    if not file_path.name.startswith("test_"):
        return None

    # check if it looks like a typsht/pytest-mypy-plugins file
    try:
        with open(file_path) as f:
            content = f.read(1000)
            if "case:" in content and "main:" in content:
                return TypeTestFile.from_parent(parent, path=file_path)
    except Exception:
        pass

    return None


class TypeTestFile(pytest.File):
    """collector for type test YAML files."""

    def collect(self):
        """yield test items from this file."""
        cases = parse_yaml_cases(self.path)
        for case in cases:
            yield TypeTestItem.from_parent(self, name=case.name, case=case)


class TypeTestItem(pytest.Item):
    """a single type test case."""

    def __init__(self, name: str, parent: pytest.Collector, case: TypeTestCase) -> None:
        super().__init__(name, parent)
        self.case = case

    def runtest(self) -> None:
        """run the type checking test."""
        source = SourceInput(content=self.case.main)

        for checker_type in self.case.checkers:
            checker = get_checker(checker_type)
            result = checker.check(source)

            # get expected output for this checker
            expected = self.case.checker_outputs.get(
                checker_type, self.case.expected_output
            )

            if expected is not None:
                self._assert_output(result.output, expected, checker_type)
            elif self.case.should_pass is not None:
                if self.case.should_pass and not result.success:
                    raise TypeTestFailure(
                        f"{checker_type.value} failed unexpectedly:\n{result.output}"
                    )
                elif not self.case.should_pass and result.success:
                    raise TypeTestFailure(
                        f"{checker_type.value} passed but was expected to fail"
                    )

    def _assert_output(self, actual: str, expected: str, checker: CheckerType) -> None:
        """assert output matches expected pattern."""
        if self.case.regex:
            pattern = re.compile(expected, re.MULTILINE | re.DOTALL)
            if not pattern.search(actual):
                raise TypeTestFailure(
                    f"{checker.value} output did not match regex:\n"
                    f"expected pattern: {expected}\n"
                    f"actual output:\n{actual}"
                )
        else:
            # normalize whitespace and compare
            expected_norm = " ".join(expected.split())
            actual_norm = " ".join(actual.split())
            if expected_norm not in actual_norm:
                raise TypeTestFailure(
                    f"{checker.value} output did not match:\n"
                    f"expected: {expected}\n"
                    f"actual:\n{actual}"
                )

    def repr_failure(self, excinfo: Any) -> str:  # type: ignore[override]
        """format failure message."""
        if isinstance(excinfo.value, TypeTestFailure):
            return str(excinfo.value)
        result = super().repr_failure(excinfo)
        return str(result)

    def reportinfo(self) -> tuple[Path, None, str]:
        """return location info for test reporting."""
        return self.path, None, f"typetest: {self.name}"


# ---------------------------------------------------------------------------
# programmatic assertion helpers
# ---------------------------------------------------------------------------


def assert_type_equals(
    code: str,
    line: int,
    expected_type: str,
    checkers: list[CheckerType] | None = None,
) -> None:
    """assert that reveal_type on a line produces expected type.

    example:
        assert_type_equals('''
            x: int = 1
            reveal_type(x)
        ''', line=2, expected_type="int")

    args:
        code: python source code containing reveal_type call
        line: line number where reveal_type is called
        expected_type: expected type string (will be normalized)
        checkers: which checkers to run (default: mypy, pyright)
    """
    if checkers is None:
        checkers = [CheckerType.MYPY, CheckerType.PYRIGHT]

    source = SourceInput(content=code)

    for checker_type in checkers:
        checker = get_checker(checker_type)
        result = checker.check(source)
        parsed = parse_output(result.output, checker_type)

        actual = parsed.revealed_types.get(line)
        if actual is None:
            raise AssertionError(
                f"{checker_type.value}: no revealed type on line {line}\n"
                f"available reveals: {parsed.revealed_types}\n"
                f"output: {result.output}"
            )

        expected_norm = normalize_type(expected_type, checker_type)
        if actual != expected_norm:
            raise AssertionError(
                f"{checker_type.value}: type mismatch on line {line}\n"
                f"expected: {expected_norm}\n"
                f"actual: {actual}"
            )


def assert_type_error(
    code: str,
    line: int | None = None,
    error_pattern: str | None = None,
    checkers: list[CheckerType] | None = None,
) -> None:
    """assert that code produces a type error.

    example:
        assert_type_error('''
            def foo(x: int) -> str:
                return x
        ''', line=2, error_pattern="incompatible return")

    args:
        code: python source code that should produce an error
        line: optional line number where error is expected
        error_pattern: optional regex pattern to match in error message
        checkers: which checkers to run (default: mypy, pyright)
    """
    if checkers is None:
        checkers = [CheckerType.MYPY, CheckerType.PYRIGHT]

    source = SourceInput(content=code)

    for checker_type in checkers:
        checker = get_checker(checker_type)
        result = checker.check(source)

        if result.success:
            raise AssertionError(
                f"{checker_type.value}: expected error but check passed"
            )

        parsed = parse_output(result.output, checker_type)

        if line is not None:
            line_errors = [e for e in parsed.errors if e[0] == line]
            if not line_errors:
                raise AssertionError(
                    f"{checker_type.value}: no error on line {line}\n"
                    f"errors found: {[(e[0], e[2]) for e in parsed.errors]}"
                )

        if error_pattern is not None:
            pattern = re.compile(error_pattern, re.IGNORECASE)
            matching = [e for e in parsed.errors if pattern.search(e[2])]
            if not matching:
                raise AssertionError(
                    f"{checker_type.value}: no error matching '{error_pattern}'\n"
                    f"error messages: {[e[2] for e in parsed.errors]}"
                )


def assert_no_errors(
    code: str,
    checkers: list[CheckerType] | None = None,
) -> None:
    """assert that code passes type checking.

    example:
        assert_no_errors('''
            def foo(x: int) -> int:
                return x
        ''')

    args:
        code: python source code that should pass type checking
        checkers: which checkers to run (default: mypy, pyright)
    """
    if checkers is None:
        checkers = [CheckerType.MYPY, CheckerType.PYRIGHT]

    source = SourceInput(content=code)

    for checker_type in checkers:
        checker = get_checker(checker_type)
        result = checker.check(source)

        if not result.success:
            raise AssertionError(
                f"{checker_type.value}: unexpected errors\n{result.output}"
            )
