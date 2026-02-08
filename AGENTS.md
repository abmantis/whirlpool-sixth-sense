# AGENTS.md - Guidelines for AI Coding Agents

This document provides essential information for AI coding agents working in this repository.

## Project Overview

- **Language**: Python 3.11+
- **Type**: Asyncio-based API library for Whirlpool 6th Sense smart appliances
- **Package**: `whirlpool_sixth_sense`

## Build & Development Commands

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest --log-cli-level=debug

# Run a single test file
pytest tests/test_auth.py

# Run a single test function
pytest tests/test_auth.py::test_auth_success

# Run tests matching a pattern
pytest -k "test_attributes"

# Linting
ruff check .              # Check for lint errors
ruff check . --fix        # Auto-fix lint errors

# Type checking
basedpyright

# Pre-commit (runs all checks)
pre-commit run --all-files
```

## Code Style Guidelines

### Imports
- Order: standard library, third-party, local
- Use relative imports within `whirlpool` package: `from .appliance import Appliance`
- Use absolute imports for external packages: `import aiohttp`

### Naming Conventions
| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `Appliance`, `AppliancesManager` |
| Functions/Methods | snake_case | `get_machine_state`, `send_attributes` |
| Constants | UPPER_SNAKE_CASE | `ATTR_MODE`, `REQUEST_RETRY_COUNT` |
| Private members | Leading underscore | `_get_attribute`, `_data_dict` |
| Enums | PascalCase class & members | `Mode.Cool`, `FanSpeed.Auto` |

### Type Annotations
- Use full type annotations throughout
- Use Python 3.11+ union syntax: `str | None` (not `Optional[str]`)
- Use `collections.abc` for generic types: `Callable`, `Generator`, `AsyncGenerator`
- Examples:
  ```python
  def get_value(self) -> int | None:
  async def fetch_data(self, timeout: float = 30.0) -> dict[str, str]:
  ```

### Async Patterns
- Use `async`/`await` for all I/O operations
- Use `aiohttp.ClientSession` for HTTP requests
- Use `async_timeout` for request timeouts
- Pass session objects rather than creating new ones

### Error Handling
- Use custom exceptions for specific error cases (e.g., `AccountLockedError`)
- Log errors using the module logger
- Return `False` or `None` for recoverable failures rather than raising exceptions
- Implement retry logic for network requests (`REQUEST_RETRY_COUNT = 3`)

### Logging
- Define module-level logger: `LOGGER = logging.getLogger(__name__)`
- Use appropriate log levels: `debug` for verbose, `error` for failures
- Use f-strings in log messages

### Class Design
- Base `Appliance` class with common functionality in `appliance.py`
- Appliance-specific classes inherit and extend with device-specific methods
- Use `@property` for computed values, `@dataclass` for data containers, `Enum` for constants

## Testing Guidelines

### Framework
- pytest with pytest-asyncio (async tests auto-detected via `asyncio_mode = auto`)
- Use `aioresponses` for mocking HTTP requests

### Test Structure
```python
async def test_feature_success(
    auth: Auth,
    backend_selector: BackendSelector,
    aioresponses_mock: aioresponses
):
    # Arrange
    aioresponses_mock.post(url, payload=mock_data)
    # Act
    result = await auth.do_auth(store=False)
    # Assert
    assert result is True
    assert auth.is_access_token_valid()
```

### Available Fixtures (from `tests/conftest.py`)
- `aioresponses_mock` - Mock HTTP responses
- `client_session_fixture` - Shared aiohttp session
- `backend_selector` - BackendSelector instance
- `auth` - Auth instance with mock credentials
- `appliances_manager` - Fully configured manager

### Mock Data
- Store mock JSON responses in `tests/data/`
- Load with: `DATA_DIR / "filename.json"`

## Linting Configuration (ruff)

Enabled rules: `E` (pycodestyle), `F` (Pyflakes), `UP` (pyupgrade), `B` (flake8-bugbear), `I` (isort)

Max complexity: 25

## CI/CD Pipeline

GitHub Actions runs on push/PR:
1. **pyright** - Type checking (Python 3.12, 3.13)
2. **ruff** - Linting
3. **pytest** - Tests (Python 3.12, 3.13)
4. **release** - Semantic release to PyPI (master branch only)

