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
