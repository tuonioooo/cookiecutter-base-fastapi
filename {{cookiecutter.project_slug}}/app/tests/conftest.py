import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """
    TestClient fixture for FastAPI app
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def hero_payload():
    """
    Sample hero data for tests
    """
    return {
        "name": "测试英雄",
        "age": 25,
        "secret_name": "测试秘密身份"
    } 