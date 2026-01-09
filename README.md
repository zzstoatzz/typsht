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

## pytest plugin

typsht includes a pytest plugin for running type safety tests across multiple type checkers. the key feature is **inline assertions** that work identically across mypy, pyright, and ty.

### inline assertions (checker-agnostic)

use `# R: type` for reveal_type assertions and `# E: pattern` for error assertions:

```yaml
- case: reveal_type_works_across_checkers
  checkers: [mypy, pyright, ty]
  main: |
    x: list[str] = ["a", "b"]
    reveal_type(x)  # R: list[str]

- case: error_detected_across_checkers
  checkers: [mypy, pyright, ty]
  main: |
    def foo(x: int) -> str:
        return x  # E: return
```

the plugin normalizes type representations (`builtins.int` -> `int`, `List` -> `list`, `Literal[42]` -> `int`) so the same assertion works across all checkers.

### legacy format (pytest-mypy-plugins compatible)

also supports the [pytest-mypy-plugins](https://github.com/typeddjango/pytest-mypy-plugins) format for migrating existing tests:

```yaml
- case: mypy_specific_output
  main: |
    x: int = 42
    reveal_type(x)
  out: 'Revealed type is "builtins.int"'

- case: should_pass_check
  main: |
    def add(a: int, b: int) -> int:
        return a + b
  should_pass: true
```

run the tests:
```bash
pytest tests/typesafety/
```

### programmatic assertions

for python tests, use the assertion helpers directly:

```python
from typsht import assert_type_equals, assert_type_error, assert_no_errors, CheckerType

def test_reveal_type():
    assert_type_equals('''
        x: int = 1
        reveal_type(x)
    ''', line=2, expected_type="int", checkers=[CheckerType.MYPY, CheckerType.PYRIGHT, CheckerType.TY])

def test_catches_error():
    assert_type_error('''
        def foo(x: int) -> str:
            return x
    ''', error_pattern="return", checkers=[CheckerType.MYPY, CheckerType.PYRIGHT, CheckerType.TY])

def test_valid_code():
    assert_no_errors('''
        def add(a: int, b: int) -> int:
            return a + b
    ''', checkers=[CheckerType.MYPY, CheckerType.PYRIGHT, CheckerType.TY])
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
