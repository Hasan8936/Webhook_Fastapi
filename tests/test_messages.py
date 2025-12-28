import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_messages_pagination_default():
    """Test /messages endpoint with default pagination"""
    response = client.get("/messages")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["limit"] == 50
    assert data["offset"] == 0


def test_messages_pagination_custom():
    """Test /messages endpoint with custom limit/offset"""
    response = client.get("/messages?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 10
    assert data["offset"] == 0


def test_messages_pagination_bounds():
    """Test /messages endpoint respects limit bounds"""
    # limit > 100 should be clamped to 100
    response = client.get("/messages?limit=200&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 100
    
    # limit < 1 should be clamped to 1
    response = client.get("/messages?limit=0&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 1


def test_messages_filter_from():
    """Test /messages endpoint filter by from"""
    response = client.get("/messages?from_=%2B919876543210")  # URL encoded
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


def test_messages_filter_since():
    """Test /messages endpoint filter by since"""
    response = client.get("/messages?since=2025-01-15T00:00:00Z")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


def test_messages_filter_search():
    """Test /messages endpoint text search"""
    response = client.get("/messages?q=hello")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


def test_messages_combined_filters():
    """Test /messages endpoint with multiple filters"""
    response = client.get("/messages?limit=25&offset=0&from_=%2B919876543210&since=2025-01-15T00:00:00Z&q=test")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 25
    assert data["offset"] == 0
    assert "data" in data
