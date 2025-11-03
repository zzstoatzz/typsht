"""tests for type definitions."""

from pathlib import Path

import pytest

from typsht._internal.types import SourceInput


def test_source_input_with_content() -> None:
    """test creating SourceInput with content."""
    source = SourceInput(content="def foo(): pass")
    assert source.content == "def foo(): pass"
    assert source.path is None


def test_source_input_with_path() -> None:
    """test creating SourceInput with path."""
    path = Path("test.py")
    source = SourceInput(path=path)
    assert source.content is None
    assert source.path == path


def test_source_input_requires_one() -> None:
    """test that SourceInput requires either content or path."""
    with pytest.raises(ValueError, match="must provide either content or path"):
        SourceInput()


def test_source_input_not_both() -> None:
    """test that SourceInput cannot have both content and path."""
    with pytest.raises(ValueError, match="cannot provide both content and path"):
        SourceInput(content="def foo(): pass", path=Path("test.py"))
