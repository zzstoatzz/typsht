"""tests for parallel runner."""

from typsht._internal.runner import run_all_checkers
from typsht._internal.types import CheckerType, SourceInput


def test_run_all_checkers() -> None:
    """test running all checkers in parallel."""
    source = SourceInput(content="def foo(x: int) -> int:\n    return x")
    results = run_all_checkers(source)

    # should have results for all checkers
    assert len(results) == len(CheckerType)
    assert all(checker in results for checker in CheckerType)

    # all results should have the correct types
    for checker, result in results.items():
        assert result.checker == checker
        assert isinstance(result.duration, float)


def test_run_specific_checkers() -> None:
    """test running specific checkers only."""
    source = SourceInput(content="def foo(x: int) -> int:\n    return x")
    checkers = [CheckerType.MYPY, CheckerType.PYRIGHT]
    results = run_all_checkers(source, checkers)

    # should only have results for specified checkers
    assert len(results) == 2
    assert CheckerType.MYPY in results
    assert CheckerType.PYRIGHT in results
    assert CheckerType.PYRE not in results


def test_invalid_code_results() -> None:
    """test that invalid code fails type checking."""
    source = SourceInput(content="def foo(x: int) -> str:\n    return x")
    results = run_all_checkers(source, [CheckerType.MYPY])

    # mypy should catch the type error
    assert not results[CheckerType.MYPY].success
