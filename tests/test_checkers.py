"""tests for type checkers."""

from typsht._internal.checkers import (
    MypyChecker,
    PyreChecker,
    PyrightChecker,
    get_checker,
)
from typsht._internal.types import CheckerType, SourceInput


def test_get_mypy_checker() -> None:
    """test getting mypy checker."""
    checker = get_checker(CheckerType.MYPY)
    assert isinstance(checker, MypyChecker)
    assert checker.checker_type == CheckerType.MYPY


def test_get_pyright_checker() -> None:
    """test getting pyright checker."""
    checker = get_checker(CheckerType.PYRIGHT)
    assert isinstance(checker, PyrightChecker)
    assert checker.checker_type == CheckerType.PYRIGHT


def test_get_pyre_checker() -> None:
    """test getting pyre checker."""
    checker = get_checker(CheckerType.PYRE)
    assert isinstance(checker, PyreChecker)
    assert checker.checker_type == CheckerType.PYRE


def test_mypy_checker_valid_code() -> None:
    """test mypy checker on valid code."""
    checker = MypyChecker()
    source = SourceInput(content="def foo(x: int) -> int:\n    return x")
    result = checker.check(source)

    assert result.checker == CheckerType.MYPY
    assert isinstance(result.duration, float)
    assert result.duration > 0


def test_mypy_checker_invalid_code() -> None:
    """test mypy checker on invalid code."""
    checker = MypyChecker()
    source = SourceInput(content="def foo(x: int) -> str:\n    return x")
    result = checker.check(source)

    assert result.checker == CheckerType.MYPY
    assert not result.success
    assert result.exit_code != 0
