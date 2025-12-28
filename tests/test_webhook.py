import pytest
import hmac
import hashlib
import json
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)
WEBHOOK_SECRET = "supersecret"


def test_webhook_valid_insert():
    """Test valid webhook insert creates message"""
    payload = {
        "message_id": "test_msg_1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello World"
    }
    raw = json.dumps(payload).encode()
    sig = hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    
    response = client.post(
        "/webhook",
        content=raw,
        headers={"X-Signature": sig, "Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_webhook_duplicate():
    """Test duplicate message_id returns 200 (idempotent)"""
    payload = {
        "message_id": "test_msg_2",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:01Z",
        "text": "Duplicate test"
    }
    raw = json.dumps(payload).encode()
    sig = hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    
    # First insert
    response1 = client.post(
        "/webhook",
        content=raw,
        headers={"X-Signature": sig, "Content-Type": "application/json"}
    )
    assert response1.status_code == 200
    
    # Duplicate insert
    response2 = client.post(
        "/webhook",
        content=raw,
        headers={"X-Signature": sig, "Content-Type": "application/json"}
    )
    assert response2.status_code == 200


def test_webhook_invalid_signature():
    """Test invalid signature returns 401"""
    payload = {
        "message_id": "test_msg_3",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:02Z",
        "text": "Invalid sig test"
    }
    raw = json.dumps(payload).encode()
    
    response = client.post(
        "/webhook",
        content=raw,
        headers={"X-Signature": "invalid_signature", "Content-Type": "application/json"}
    )
    assert response.status_code == 401


def test_webhook_missing_signature():
    """Test missing signature returns 401"""
    payload = {
        "message_id": "test_msg_4",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:03Z",
        "text": "Missing sig test"
    }
    raw = json.dumps(payload).encode()
    
    response = client.post(
        "/webhook",
        content=raw,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 401


def test_webhook_invalid_json():
    """Test invalid JSON returns 422"""
    response = client.post(
        "/webhook",
        content=b"not valid json",
        headers={"X-Signature": "somesig", "Content-Type": "application/json"}
    )
    assert response.status_code == 422


def test_webhook_validation_error():
    """Test invalid message model returns 422"""
    payload = {
        "message_id": "",  # empty - should fail
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:04Z",
        "text": "Validation test"
    }
    raw = json.dumps(payload).encode()
    sig = hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    
    response = client.post(
        "/webhook",
        content=raw,
        headers={"X-Signature": sig, "Content-Type": "application/json"}
    )
    assert response.status_code == 422
