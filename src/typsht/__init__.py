"""typsht - type checker agnostic parallel type checking tool."""

__version__ = "0.0.0"

from typsht._internal.pytest_plugin import (
    assert_no_errors,
    assert_type_equals,
    assert_type_error,
)
from typsht._internal.types import CheckerType
