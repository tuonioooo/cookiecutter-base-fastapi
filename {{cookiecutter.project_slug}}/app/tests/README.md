# Hero API Tests

This directory contains tests for the Hero API endpoints using pytest.

## Running the Tests

Make sure you have the required dependencies installed:

```bash
uv add pytest pytest-cov httpx
# 或
pip install pytest pytest-cov httpx
```

To run all tests:

```bash
# From the project root
pytest app/tests -v
```

run errors  `E AttributeError: module 'httpcore' has no attribute 'Request'`

```bash
uv remove httpcore #或 pip uninstall httpcore
uv add httpcore==1.0.7
```

To run tests with coverage report:

```bash
pytest app/tests --cov=app -v
```

## Test Files

- `test_hero.py` - Tests for the Hero API endpoints
- `conftest.py` - Pytest fixtures for the tests

## Test Coverage

The tests cover all Hero API endpoints:

- GET /heroes - Get hero list with pagination and filtering
- GET /heroes/{hero_id} - Get single hero by ID
- POST /heroes - Create a new hero
- PUT /heroes/{hero_id} - Update an existing hero
- DELETE /heroes/{hero_id} - Delete a hero 