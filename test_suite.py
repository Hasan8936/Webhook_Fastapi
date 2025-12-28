#!/usr/bin/env python3
"""
Comprehensive Test Suite for Lyra Webhook API
Tests all endpoints according to project specifications
"""

import requests
import json
import hmac
import hashlib
import sys
from datetime import datetime
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:8000"
WEBHOOK_SECRET = "test-secret-key"

class WebhookTester:
    def __init__(self):
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

    def generate_hmac(self, payload: str) -> str:
        """Generate HMAC-SHA256 signature"""
        return hmac.new(
            WEBHOOK_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    def test_endpoint(self, test_name: str, method: str, endpoint: str, 
                     body: dict = None, expected_status: int = 200, 
                     headers: dict = None) -> Tuple[bool, str]:
        """Test an API endpoint"""
        self.total_tests += 1
        url = f"{BASE_URL}{endpoint}"
        
        try:
            if headers is None:
                headers = {}
            headers["Content-Type"] = "application/json"
            
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, json=body, headers=headers)
            else:
                return False, "Unknown method"
            
            status_ok = response.status_code == expected_status
            
            if status_ok:
                self.passed_tests += 1
                status = "✅ PASS"
            else:
                self.failed_tests += 1
                status = "❌ FAIL"
            
            result = {
                "test_name": test_name,
                "method": method,
                "endpoint": endpoint,
                "expected_status": expected_status,
                "actual_status": response.status_code,
                "status": status,
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
            
            self.results.append(result)
            print(f"{status} | {test_name} (Expected: {expected_status}, Got: {response.status_code})")
            
            return status_ok, response.text[:100]
        
        except Exception as e:
            self.failed_tests += 1
            self.results.append({
                "test_name": test_name,
                "method": method,
                "endpoint": endpoint,
                "expected_status": expected_status,
                "actual_status": "ERROR",
                "status": "❌ FAIL",
                "error": str(e)
            })
            print(f"❌ FAIL | {test_name} - {str(e)}")
            return False, str(e)

    def run_all_tests(self):
        """Run all tests"""
        print("=" * 70)
        print("LYRA WEBHOOK API - COMPREHENSIVE TEST SUITE")
        print("=" * 70)
        print()
        
        # Health Probes
        print("🔍 HEALTH PROBES")
        self.test_endpoint("Health Liveness Probe", "GET", "/health/live", expected_status=200)
        self.test_endpoint("Health Readiness Probe", "GET", "/health/ready", expected_status=200)
        print()
        
        # HMAC Signature Tests
        print("🔐 HMAC SIGNATURE VALIDATION")
        invalid_payload = json.dumps({
            "message_id": "test-001",
            "from_": "+1234567890",
            "to": "+9876543210",
            "body": "Test message"
        })
        self.test_endpoint(
            "Reject Invalid Signature",
            "POST", "/webhook",
            body=json.loads(invalid_payload),
            expected_status=401,
            headers={"X-Webhook-Signature": "invalidsignature"}
        )
        
        valid_payload = json.dumps({
            "message_id": "msg-valid-001",
            "from_": "+1111111111",
            "to": "+2222222222",
            "body": "Valid message with correct signature"
        })
        valid_sig = self.generate_hmac(valid_payload)
        self.test_endpoint(
            "Accept Valid Signature",
            "POST", "/webhook",
            body=json.loads(valid_payload),
            expected_status=200,
            headers={"X-Webhook-Signature": valid_sig}
        )
        
        self.test_endpoint(
            "Detect Duplicate Message",
            "POST", "/webhook",
            body=json.loads(valid_payload),
            expected_status=200,
            headers={"X-Webhook-Signature": valid_sig}
        )
        print()
        
        # Validation Tests
        print("✔️  INPUT VALIDATION")
        invalid_phone_payload = json.dumps({
            "message_id": "msg-bad-phone",
            "from_": "invalid-phone",
            "to": "+2222222222",
            "body": "Bad phone number"
        })
        bad_phone_sig = self.generate_hmac(invalid_phone_payload)
        self.test_endpoint(
            "Reject Invalid Phone Format",
            "POST", "/webhook",
            body=json.loads(invalid_phone_payload),
            expected_status=422,
            headers={"X-Webhook-Signature": bad_phone_sig}
        )
        
        incomplete_payload = json.dumps({"message_id": "msg-incomplete"})
        incomplete_sig = self.generate_hmac(incomplete_payload)
        self.test_endpoint(
            "Reject Missing Required Fields",
            "POST", "/webhook",
            body=json.loads(incomplete_payload),
            expected_status=422,
            headers={"X-Webhook-Signature": incomplete_sig}
        )
        print()
        
        # Create test messages
        print("📝 CREATING TEST MESSAGES")
        for i in range(1, 4):
            payload = json.dumps({
                "message_id": f"msg-list-{i}",
                "from_": f"+11111111{i}",
                "to": f"+22222222{i}",
                "body": f"Test message number {i}"
            })
            sig = self.generate_hmac(payload)
            self.test_endpoint(
                f"Create Message {i}",
                "POST", "/webhook",
                body=json.loads(payload),
                expected_status=200,
                headers={"X-Webhook-Signature": sig}
            )
        print()
        
        # Message Retrieval Tests
        print("📋 MESSAGE RETRIEVAL & FILTERING")
        self.test_endpoint("List Messages (Limit 10)", "GET", "/messages?limit=10&offset=0", expected_status=200)
        self.test_endpoint("List Messages (Limit 2)", "GET", "/messages?limit=2&offset=0", expected_status=200)
        self.test_endpoint("Filter by Sender", "GET", "/messages?from_=%2B1111111111", expected_status=200)
        self.test_endpoint("Search by Keyword", "GET", "/messages?q=message", expected_status=200)
        print()
        
        # Analytics & Metrics
        print("📊 ANALYTICS & METRICS")
        self.test_endpoint("Get Statistics", "GET", "/stats", expected_status=200)
        self.test_endpoint("Get Prometheus Metrics", "GET", "/metrics", expected_status=200)
        print()
        
        # Summary
        print("=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {self.total_tests}")
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        if self.total_tests > 0:
            success_rate = (self.passed_tests / self.total_tests) * 100
            print(f"Success Rate: {success_rate:.2f}%")
        print()
        
        return self.results

if __name__ == "__main__":
    tester = WebhookTester()
    results = tester.run_all_tests()
    
    # Export results
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    sys.exit(0 if tester.failed_tests == 0 else 1)
