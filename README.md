# typsht

type checker agnostic parallel type checking tool. run multiple python type checkers (mypy, pyright, ty, pyre) in parallel on the same code.

inspired by tox, but specifically for type checkers. get comprehensive type checking coverage by running multiple type checkers simultaneously.

## installation

### quick start (no installation)

use `uvx` to run typsht without installing it:

```bash
# check inline code
uvx typsht 'def foo(x: int) -> str: return x'

# check a file
uvx typsht --file my_module.py
```

### install to your project

```bash
uv add typsht
```

## usage

check inline code:
```bash
# this will catch the type error across all checkers
typsht 'def foo(x: int) -> str: return x'
```

check a file:
```bash
typsht --file my_module.py
```

run specific type checkers:
```bash
typsht --file my_module.py --checkers mypy --checkers ty
```

show detailed output from each checker:
```bash
typsht --file my_module.py --verbose
```

### project support

typsht automatically detects when checking files in a uv project (containing `pyproject.toml` or `uv.lock`) and runs type checkers using `uv run --project`, giving them access to your local development packages.

this is useful for library developers who want to verify type annotations work across multiple checkers:

```bash
# in a project with local packages installed in editable mode
uvx typsht --file repros/test_case.py --verbose

# type checkers will have access to your local package imports
```

inline code always runs in an isolated environment.

## supported type checkers

by default, typsht runs:
- **mypy** - widely adopted static type checker
- **pyright** - fast static type checker from microsoft
- **ty** - experimental blazing-fast type checker

also available (requires project configuration):
- **pyre** - facebook's type checker (requires .pyre_configuration)

## development

install dependencies:
```bash
uv sync
```

run tests:
```bash
uv run pytest
```

install pre-commit hooks:
```bash
uv run pre-commit install
```
