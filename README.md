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

typsht includes a pytest plugin for running type safety tests. it's compatible with the [pytest-mypy-plugins](https://github.com/typeddjango/pytest-mypy-plugins) YAML format, making it easy to migrate existing tests or run them across multiple type checkers.

### yaml test format

create YAML files in your test directory (e.g., `tests/typesafety/test_types.yml`):

```yaml
- case: simple_reveal_type
  main: |
    x: int = 42
    reveal_type(x)
  out: 'Revealed type is "builtins.int"'

- case: function_return_type_error
  main: |
    def foo(x: int) -> str:
        return x
  regex: yes
  out: 'error:.*[Ii]ncompatible return'

- case: valid_code_should_pass
  main: |
    def add(a: int, b: int) -> int:
        return a + b
  should_pass: true

- case: multi_checker_test
  main: |
    x: list[int] = [1, 2, 3]
    reveal_type(x)
  checkers: [mypy, pyright]
  out_mypy: 'Revealed type is "builtins.list[builtins.int]"'
  out_pyright: 'Type of "x" is "list[int]"'
```

run the tests:
```bash
pytest tests/typesafety/
```

### programmatic assertions

for more flexibility, use the assertion helpers directly in Python tests:

```python
from typsht import assert_type_equals, assert_type_error, assert_no_errors, CheckerType

def test_reveal_type():
    assert_type_equals('''
        x: int = 1
        reveal_type(x)
    ''', line=2, expected_type="int")

def test_catches_error():
    assert_type_error('''
        def foo(x: int) -> str:
            return x
    ''', line=2, error_pattern="incompatible return")

def test_valid_code():
    assert_no_errors('''
        def add(a: int, b: int) -> int:
            return a + b
    ''')

def test_multi_checker():
    assert_type_equals('''
        x: list[int] = [1]
        reveal_type(x)
    ''', line=2, expected_type="list[int]", checkers=[CheckerType.MYPY, CheckerType.PYRIGHT])
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
