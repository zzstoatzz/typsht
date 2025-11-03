"""CLI for typsht."""

import sys
from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter
from rich.console import Console

from typsht._internal.runner import (
    display_detailed_output,
    display_results,
    run_all_checkers,
)
from typsht._internal.types import CheckerType, SourceInput

console = Console()
app = App(help="run type checkers in parallel on python code")


@app.default
def main(
    source: Annotated[
        str | None,
        Parameter(show=False),
    ] = None,
    *,
    file: Annotated[
        Path | None,
        Parameter(
            name=["--file", "-f"],
            help="path to python file to check",
        ),
    ] = None,
    checkers: Annotated[
        list[str] | None,
        Parameter(
            name=["--checkers", "-c"],
            help="specific type checkers to run (default: mypy, pyright, ty)",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        Parameter(
            name=["--verbose", "-v"],
            help="show detailed output from each checker",
        ),
    ] = False,
    debug: Annotated[
        bool,
        Parameter(
            name=["--debug"],
            help="show debug information including command execution details",
        ),
    ] = False,
) -> None:
    """run type checkers in parallel on python code.

    provide either:
    - raw python code as SOURCE argument
    - a file path with --file/-f flag

    examples:
        typsht "def foo(x: int) -> str: return x"
        typsht --file my_module.py
        typsht --file my_module.py --checkers mypy --checkers ty
    """
    # validate input
    if not source and not file:
        console.print(
            "[red]error: must provide either source code or --file flag[/red]"
        )
        sys.exit(1)

    if source and file:
        console.print("[red]error: cannot provide both source and --file[/red]")
        sys.exit(1)

    # validate file exists
    if file and not file.exists():
        console.print(f"[red]error: file not found: {file}[/red]")
        sys.exit(1)

    # create source input
    if file:
        source_input = SourceInput(path=file)
        console.print(f"[dim]checking file: {file}[/dim]\n")
    else:
        source_input = SourceInput(content=source)
        console.print("[dim]checking inline code[/dim]\n")

    # select checkers (default to mypy, pyright, and ty)
    if checkers is not None:
        # validate checker names
        valid_checkers = {c.value for c in CheckerType}
        invalid = [c for c in checkers if c not in valid_checkers]
        if invalid:
            console.print(f"[red]error: invalid checkers: {', '.join(invalid)}[/red]")
            console.print(f"[dim]valid options: {', '.join(valid_checkers)}[/dim]")
            sys.exit(1)
        selected_checkers = [CheckerType(c) for c in checkers]
    else:
        selected_checkers = [CheckerType.MYPY, CheckerType.PYRIGHT, CheckerType.TY]

    # run type checkers
    results = run_all_checkers(source_input, selected_checkers, debug=debug)

    # display results
    display_results(results)

    if verbose:
        display_detailed_output(results)

    # exit with failure if any checker failed
    if not all(r.success for r in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    app()
