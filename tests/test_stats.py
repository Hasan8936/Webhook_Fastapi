import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_stats_endpoint():
    """Test /stats endpoint returns correct structure"""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_messages" in data
    assert "senders_count" in data
    assert "messages_per_sender" in data
    assert "first_message_ts" in data
    assert "last_message_ts" in data


def test_stats_types():
    """Test /stats endpoint returns correct types"""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["total_messages"], int)
    assert isinstance(data["senders_count"], int)
    assert isinstance(data["messages_per_sender"], list)
