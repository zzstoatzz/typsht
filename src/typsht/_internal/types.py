"""type definitions for typsht."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CheckerType(str, Enum):
    """supported type checkers."""

    MYPY = "mypy"
    PYRIGHT = "pyright"
    PYRE = "pyre"
    TY = "ty"


@dataclass
class CheckResult:
    """result from a type checker."""

    checker: CheckerType
    success: bool
    output: str
    exit_code: int
    duration: float


@dataclass
class SourceInput:
    """input source code to check."""

    content: str | None = None
    path: Path | None = None
    project_root: Path | None = None  # explicit project root for context

    def __post_init__(self) -> None:
        if not self.content and not self.path:
            raise ValueError("must provide either content or path")
        if self.content and self.path:
            raise ValueError("cannot provide both content and path")
