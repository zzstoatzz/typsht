"""type checker implementations."""

import subprocess
import tempfile
import time
from pathlib import Path

from typsht._internal.types import CheckerType, CheckResult, SourceInput


def find_project_root(file_path: Path) -> Path | None:
    """find the project root directory by looking for pyproject.toml or uv.lock.

    walks up the directory tree from the given file path until it finds
    a directory containing pyproject.toml or uv.lock.

    returns None if no project root is found.
    """
    current = file_path.parent if file_path.is_file() else file_path

    while current != current.parent:  # stop at filesystem root
        if (current / "pyproject.toml").exists() or (current / "uv.lock").exists():
            return current
        current = current.parent

    return None


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
                # use explicit project_root if provided
                result = self._run_checker(temp_path, project_root=source.project_root)
            finally:
                temp_path.unlink()
        else:
            # source.path is guaranteed to be set if content is not
            assert source.path is not None
            # use explicit project_root if provided, otherwise detect
            project_root = source.project_root or find_project_root(source.path)
            result = self._run_checker(source.path, project_root=project_root)

        duration = time.time() - start
        return CheckResult(
            checker=self.checker_type,
            success=result.returncode == 0,
            output=result.stdout + result.stderr,
            exit_code=result.returncode,
            duration=duration,
        )

    def _run_checker(
        self, path: Path, project_root: Path | None
    ) -> subprocess.CompletedProcess:
        """run the specific type checker command.

        if project_root is provided, runs the checker using `uv run --project`
        to use the project's environment and dependencies.
        """
        raise NotImplementedError


class MypyChecker(TypeChecker):
    """mypy type checker."""

    def __init__(self) -> None:
        super().__init__(CheckerType.MYPY)

    def _run_checker(
        self, path: Path, project_root: Path | None
    ) -> subprocess.CompletedProcess:
        if project_root:
            # use --follow-imports=normal to ensure imports are resolved
            # when testing code that imports from local packages
            cmd = [
                "uv",
                "run",
                "--project",
                str(project_root),
                "mypy",
                "--follow-imports=normal",
                str(path),
            ]
        else:
            cmd = ["mypy", str(path)]

        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )


class PyrightChecker(TypeChecker):
    """pyright type checker."""

    def __init__(self) -> None:
        super().__init__(CheckerType.PYRIGHT)

    def _run_checker(
        self, path: Path, project_root: Path | None
    ) -> subprocess.CompletedProcess:
        if project_root:
            cmd = ["uv", "run", "--project", str(project_root), "pyright", str(path)]
        else:
            cmd = ["pyright", str(path)]

        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )


class PyreChecker(TypeChecker):
    """pyre type checker."""

    def __init__(self) -> None:
        super().__init__(CheckerType.PYRE)

    def _run_checker(
        self, path: Path, project_root: Path | None
    ) -> subprocess.CompletedProcess:
        if project_root:
            cmd = [
                "uv",
                "run",
                "--project",
                str(project_root),
                "pyre",
                "check",
                str(path),
            ]
        else:
            cmd = ["pyre", "check", str(path)]

        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )


class TyChecker(TypeChecker):
    """ty type checker."""

    def __init__(self) -> None:
        super().__init__(CheckerType.TY)

    def _run_checker(
        self, path: Path, project_root: Path | None
    ) -> subprocess.CompletedProcess:
        if project_root:
            cmd = [
                "uv",
                "run",
                "--project",
                str(project_root),
                "ty",
                "check",
                str(path),
            ]
        else:
            cmd = ["ty", "check", str(path)]

        return subprocess.run(
            cmd,
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
