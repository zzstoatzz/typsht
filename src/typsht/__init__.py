"""typsht - type checker agnostic parallel type checking tool."""

__version__ = "0.0.0"

from typsht._internal.types import CheckerType

__all__ = [
    "CheckerType",
    "assert_no_errors",
    "assert_type_equals",
    "assert_type_error",
]


def __getattr__(name: str):
    """lazy import pytest-dependent helpers."""
    if name in ("assert_no_errors", "assert_type_equals", "assert_type_error"):
        try:
            from typsht._internal.pytest_plugin import (
                assert_no_errors,
                assert_type_equals,
                assert_type_error,
            )
        except ImportError as e:
            if "pytest" in str(e):
                raise ImportError(
                    f"'{name}' requires pytest. install with: uv add pytest"
                ) from None
            raise
        return {
            "assert_no_errors": assert_no_errors,
            "assert_type_equals": assert_type_equals,
            "assert_type_error": assert_type_error,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
