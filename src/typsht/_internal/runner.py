"""parallel type checker execution."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.table import Table

from typsht._internal.checkers import get_checker
from typsht._internal.types import CheckerType, CheckResult, SourceInput

console = Console()


def run_all_checkers(
    source: SourceInput,
    checkers: list[CheckerType] | None = None,
    debug: bool = False,
) -> dict[CheckerType, CheckResult]:
    """run all type checkers in parallel.

    uses ThreadPoolExecutor rather than ProcessPoolExecutor because:
    - each checker spawns a subprocess (mypy, pyright, ty)
    - threads have lower overhead for managing subprocess I/O
    - empirical benchmarks show 14% faster execution with threads
    - threads use less memory (no process forking overhead)

    see sandbox/benchmark_executors.py for benchmark results.
    """
    if checkers is None:
        checkers = list(CheckerType)

    results: dict[CheckerType, CheckResult] = {}

    if debug:
        console.print(f"[dim]running {len(checkers)} type checkers in parallel[/dim]")

    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(get_checker(checker).check, source): checker
            for checker in checkers
        }

        for future in as_completed(futures):
            checker = futures[future]
            try:
                result = future.result()
                results[checker] = result
                if debug:
                    console.print(
                        f"[dim]{checker.value} completed in {result.duration:.3f}s "
                        f"(exit code: {result.exit_code})[/dim]"
                    )
            except Exception as e:
                console.print(f"[red]error running {checker}: {e}[/red]")

    return results


def display_results(results: dict[CheckerType, CheckResult]) -> None:
    """display type checking results in a table."""
    table = Table(title="type checking results")

    table.add_column("checker", style="cyan")
    table.add_column("status", style="magenta")
    table.add_column("duration", justify="right", style="green")
    table.add_column("exit code", justify="right")

    for checker, result in results.items():
        status = "✓ pass" if result.success else "✗ fail"
        status_style = "green" if result.success else "red"

        table.add_row(
            checker.value,
            f"[{status_style}]{status}[/{status_style}]",
            f"{result.duration:.2f}s",
            str(result.exit_code),
        )

    console.print(table)


def display_detailed_output(results: dict[CheckerType, CheckResult]) -> None:
    """display detailed output from each checker."""
    for checker, result in results.items():
        if result.output.strip():
            console.print(f"\n[bold cyan]{checker.value} output:[/bold cyan]")
            console.print(result.output)
