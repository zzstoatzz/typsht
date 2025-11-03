"""type checker implementations."""

import subprocess
import tempfile
import time
from pathlib import Path

from typsht._internal.types import CheckerType, CheckResult, SourceInput


class TypeChecker:
    """base class for type checkers."""

    def __init__(self, checker_type: CheckerType) -> None:
        self.checker_type = checker_type

    def check(self, source: SourceInput) -> CheckResult:
        """run type checker on source."""
        start = time.time()

        # if source is raw content, write to temp file
        if source.content:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(source.content)
                temp_path = Path(f.name)
            try:
                result = self._run_checker(temp_path)
            finally:
                temp_path.unlink()
        else:
            # source.path is guaranteed to be set if content is not
            assert source.path is not None
            result = self._run_checker(source.path)

        duration = time.time() - start
        return CheckResult(
            checker=self.checker_type,
            success=result.returncode == 0,
            output=result.stdout + result.stderr,
            exit_code=result.returncode,
            duration=duration,
        )

    def _run_checker(self, path: Path) -> subprocess.CompletedProcess:
        """run the specific type checker command."""
        raise NotImplementedError


class MypyChecker(TypeChecker):
    """mypy type checker."""

    def __init__(self) -> None:
        super().__init__(CheckerType.MYPY)

    def _run_checker(self, path: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["mypy", str(path)],
            capture_output=True,
            text=True,
        )


class PyrightChecker(TypeChecker):
    """pyright type checker."""

    def __init__(self) -> None:
        super().__init__(CheckerType.PYRIGHT)

    def _run_checker(self, path: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["pyright", str(path)],
            capture_output=True,
            text=True,
        )


class PyreChecker(TypeChecker):
    """pyre type checker."""

    def __init__(self) -> None:
        super().__init__(CheckerType.PYRE)

    def _run_checker(self, path: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["pyre", "check", str(path)],
            capture_output=True,
            text=True,
        )


class TyChecker(TypeChecker):
    """ty type checker."""

    def __init__(self) -> None:
        super().__init__(CheckerType.TY)

    def _run_checker(self, path: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["ty", "check", str(path)],
            capture_output=True,
            text=True,
        )


def get_checker(checker_type: CheckerType) -> TypeChecker:
    """get a type checker instance."""
    checkers = {
        CheckerType.MYPY: MypyChecker,
        CheckerType.PYRIGHT: PyrightChecker,
        CheckerType.PYRE: PyreChecker,
        CheckerType.TY: TyChecker,
    }
    return checkers[checker_type]()
