#!/usr/bin/env python3
"""
Comprehensive webhook validation test for the Enhanced Codegen API Client
Tests actual webhook signature verification and proper event handling
"""

import os
import json
import hmac
import hashlib
from typing import Dict, Any

# Set environment variables for testing
os.environ["CODEGEN_ORG_ID"] = "323"
os.environ["CODEGEN_API_TOKEN"] = "sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99"

from api import CodegenClient, WebhookHandler, WebhookError

class WebhookTestResults:
    """Track webhook test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def success(self, test_name: str):
        print(f"✅ {test_name}")
        self.passed += 1
    
    def failure(self, test_name: str, error: str):
        print(f"❌ {test_name}: {error}")
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"WEBHOOK TEST SUMMARY: {self.passed}/{total} tests passed")
        if self.failed > 0:
            print(f"Failed tests:")
            for error in self.errors:
                print(f"  - {error}")
        print(f"{'='*60}")
        return self.failed == 0

def test_webhook_handler_initialization(results: WebhookTestResults):
    """Test webhook handler initialization"""
    print("\n🔧 Testing Webhook Handler Initialization...")
    
    try:
        # Test without secret key
        handler = WebhookHandler()
        if handler.secret_key is None and len(handler.handlers) == 0:
            results.success("Webhook handler initialization without secret")
        else:
            results.failure("Webhook handler initialization", "Unexpected initial state")
        
        # Test with secret key
        secret_key = "test-webhook-secret-key"
        handler_with_secret = WebhookHandler(secret_key=secret_key)
        if handler_with_secret.secret_key == secret_key:
            results.success("Webhook handler initialization with secret")
        else:
            results.failure("Webhook handler with secret", "Secret key not set correctly")
            
    except Exception as e:
        results.failure("Webhook handler initialization", str(e))

def test_handler_registration(results: WebhookTestResults):
    """Test webhook handler registration"""
    print("\n📝 Testing Handler Registration...")
    
    try:
        handler = WebhookHandler()
        
        # Test handler registration
        test_events = []
        
        def test_handler_1(payload: Dict[str, Any]):
            test_events.append(("handler_1", payload))
        
        def test_handler_2(payload: Dict[str, Any]):
            test_events.append(("handler_2", payload))
        
        # Register handlers
        handler.register_handler("test.event.1", test_handler_1)
        handler.register_handler("test.event.2", test_handler_2)
        
        if len(handler.handlers) == 2:
            results.success("Handler registration count")
        else:
            results.failure("Handler registration", f"Expected 2 handlers, got {len(handler.handlers)}")
        
        if "test.event.1" in handler.handlers and "test.event.2" in handler.handlers:
            results.success("Handler registration keys")
        else:
            results.failure("Handler registration", "Handler keys not registered correctly")
            
    except Exception as e:
        results.failure("Handler registration", str(e))

def test_webhook_processing_without_signature(results: WebhookTestResults):
    """Test webhook processing without signature verification"""
    print("\n🔄 Testing Webhook Processing (No Signature)...")
    
    try:
        handler = WebhookHandler()
        test_events = []
        
        def event_handler(payload: Dict[str, Any]):
            test_events.append(payload)
        
        handler.register_handler("agent_run.completed", event_handler)
        
        # Test valid payload
        valid_payload = {
            "event_type": "agent_run.completed",
            "data": {"id": 12345, "status": "completed"},
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        handler.handle_webhook(valid_payload)
        
        if len(test_events) == 1 and test_events[0] == valid_payload:
            results.success("Webhook processing without signature")
        else:
            results.failure("Webhook processing", "Event not processed correctly")
        
        # Test payload with unknown event type
        unknown_payload = {
            "event_type": "unknown.event",
            "data": {"test": "data"},
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        # This should not raise an error, just log a warning
        handler.handle_webhook(unknown_payload)
        results.success("Unknown event type handling")
        
    except Exception as e:
        results.failure("Webhook processing without signature", str(e))

def test_webhook_signature_verification(results: WebhookTestResults):
    """Test webhook signature verification"""
    print("\n🔐 Testing Webhook Signature Verification...")
    
    try:
        secret_key = "test-webhook-secret-123"
        handler = WebhookHandler(secret_key=secret_key)
        
        # Test signature verification method directly
        test_payload = {"test": "data"}
        payload_bytes = json.dumps(test_payload).encode()
        
        # Generate correct signature
        expected_signature = hmac.new(
            secret_key.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        correct_signature = f"sha256={expected_signature}"
        
        # Test correct signature
        if handler.verify_signature(payload_bytes, correct_signature):
            results.success("Correct signature verification")
        else:
            results.failure("Signature verification", "Correct signature rejected")
        
        # Test incorrect signature
        wrong_signature = "sha256=wrong_signature_hash"
        if not handler.verify_signature(payload_bytes, wrong_signature):
            results.success("Incorrect signature rejection")
        else:
            results.failure("Signature verification", "Incorrect signature accepted")
            
    except Exception as e:
        results.failure("Webhook signature verification", str(e))

def test_webhook_processing_with_signature(results: WebhookTestResults):
    """Test webhook processing with signature verification"""
    print("\n🔒 Testing Webhook Processing (With Signature)...")
    
    try:
        secret_key = "test-webhook-secret-456"
        handler = WebhookHandler(secret_key=secret_key)
        test_events = []
        
        def secure_handler(payload: Dict[str, Any]):
            test_events.append(payload)
        
        handler.register_handler("secure.event", secure_handler)
        
        # Test with correct signature
        payload = {
            "event_type": "secure.event",
            "data": {"secure": True, "id": 67890},
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        payload_bytes = json.dumps(payload).encode()
        correct_signature = hmac.new(
            secret_key.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        signature = f"sha256={correct_signature}"
        
        handler.handle_webhook(payload, signature)
        
        if len(test_events) == 1 and test_events[0] == payload:
            results.success("Webhook processing with correct signature")
        else:
            results.failure("Webhook with signature", "Event not processed with correct signature")
        
        # Test with incorrect signature
        try:
            wrong_signature = "sha256=wrong_hash_value"
            handler.handle_webhook(payload, wrong_signature)
            results.failure("Webhook signature validation", "Should have raised WebhookError")
        except WebhookError as e:
            if "Invalid webhook signature" in str(e):
                results.success("Webhook processing rejects invalid signature")
            else:
                results.failure("Webhook signature error", f"Unexpected error message: {str(e)}")
        
    except Exception as e:
        results.failure("Webhook processing with signature", str(e))

def test_webhook_error_handling(results: WebhookTestResults):
    """Test webhook error handling"""
    print("\n⚠️ Testing Webhook Error Handling...")
    
    try:
        handler = WebhookHandler()
        
        # Test missing event_type
        try:
            invalid_payload = {
                "data": {"test": "data"},
                "timestamp": "2024-01-01T00:00:00Z"
                # Missing event_type
            }
            handler.handle_webhook(invalid_payload)
            results.failure("Missing event_type", "Should have raised WebhookError")
        except WebhookError as e:
            if "Missing event_type" in str(e):
                results.success("Missing event_type error handling")
            else:
                results.failure("Missing event_type", f"Unexpected error: {str(e)}")
        
        # Test handler that raises exception
        def failing_handler(payload: Dict[str, Any]):
            raise ValueError("Handler intentionally failed")
        
        handler.register_handler("failing.event", failing_handler)
        
        try:
            failing_payload = {
                "event_type": "failing.event",
                "data": {"test": "data"},
                "timestamp": "2024-01-01T00:00:00Z"
            }
            handler.handle_webhook(failing_payload)
            results.failure("Handler exception", "Should have raised WebhookError")
        except WebhookError as e:
            if "Webhook processing failed" in str(e):
                results.success("Handler exception error handling")
            else:
                results.failure("Handler exception", f"Unexpected error: {str(e)}")
        
    except Exception as e:
        results.failure("Webhook error handling", str(e))

def test_client_webhook_integration(results: WebhookTestResults):
    """Test webhook integration with CodegenClient"""
    print("\n🔗 Testing Client Webhook Integration...")
    
    try:
        client = CodegenClient()
        
        if client.webhook_handler is not None:
            results.success("Client webhook handler initialization")
            
            # Test registering handler through client
            test_events = []
            
            def client_handler(payload: Dict[str, Any]):
                test_events.append(payload)
            
            client.webhook_handler.register_handler("client.test", client_handler)
            
            # Test processing through client
            test_payload = {
                "event_type": "client.test",
                "data": {"client_test": True},
                "timestamp": "2024-01-01T00:00:00Z"
            }
            
            client.webhook_handler.handle_webhook(test_payload)
            
            if len(test_events) == 1:
                results.success("Client webhook handler processing")
            else:
                results.failure("Client webhook processing", "Event not processed through client")
        else:
            results.failure("Client webhook integration", "Webhook handler not initialized in client")
        
        client.close()
        
    except Exception as e:
        results.failure("Client webhook integration", str(e))

def test_real_world_webhook_scenarios(results: WebhookTestResults):
    """Test real-world webhook scenarios"""
    print("\n🌍 Testing Real-World Webhook Scenarios...")
    
    try:
        secret_key = "production-webhook-secret"
        handler = WebhookHandler(secret_key=secret_key)
        
        # Track different event types
        events_received = {
            "agent_run.completed": [],
            "agent_run.failed": [],
            "agent_run.started": []
        }
        
        def track_completed(payload):
            events_received["agent_run.completed"].append(payload)
        
        def track_failed(payload):
            events_received["agent_run.failed"].append(payload)
        
        def track_started(payload):
            events_received["agent_run.started"].append(payload)
        
        # Register handlers
        handler.register_handler("agent_run.completed", track_completed)
        handler.register_handler("agent_run.failed", track_failed)
        handler.register_handler("agent_run.started", track_started)
        
        # Simulate real webhook payloads
        real_payloads = [
            {
                "event_type": "agent_run.started",
                "data": {
                    "id": 12345,
                    "organization_id": 323,
                    "status": "running",
                    "created_at": "2024-01-01T10:00:00Z"
                },
                "timestamp": "2024-01-01T10:00:00Z"
            },
            {
                "event_type": "agent_run.completed",
                "data": {
                    "id": 12345,
                    "organization_id": 323,
                    "status": "completed",
                    "result": "Task completed successfully",
                    "completed_at": "2024-01-01T10:05:00Z"
                },
                "timestamp": "2024-01-01T10:05:00Z"
            },
            {
                "event_type": "agent_run.failed",
                "data": {
                    "id": 12346,
                    "organization_id": 323,
                    "status": "failed",
                    "error": "Task failed due to timeout",
                    "failed_at": "2024-01-01T10:03:00Z"
                },
                "timestamp": "2024-01-01T10:03:00Z"
            }
        ]
        
        # Process each payload with proper signatures
        for payload in real_payloads:
            payload_bytes = json.dumps(payload).encode()
            signature = hmac.new(
                secret_key.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            handler.handle_webhook(payload, f"sha256={signature}")
        
        # Verify all events were processed correctly
        if (len(events_received["agent_run.started"]) == 1 and
            len(events_received["agent_run.completed"]) == 1 and
            len(events_received["agent_run.failed"]) == 1):
            results.success("Real-world webhook scenario processing")
        else:
            results.failure("Real-world scenarios", "Not all events processed correctly")
        
        # Verify event data integrity
        completed_event = events_received["agent_run.completed"][0]
        if completed_event["data"]["id"] == 12345 and completed_event["data"]["result"] == "Task completed successfully":
            results.success("Webhook payload data integrity")
        else:
            results.failure("Payload integrity", "Event data not preserved correctly")
            
    except Exception as e:
        results.failure("Real-world webhook scenarios", str(e))

def main():
    """Run comprehensive webhook validation tests"""
    print("🔗 Starting Comprehensive Webhook Validation Tests")
    print("=" * 60)
    
    results = WebhookTestResults()
    
    # Run all webhook tests
    test_webhook_handler_initialization(results)
    test_handler_registration(results)
    test_webhook_processing_without_signature(results)
    test_webhook_signature_verification(results)
    test_webhook_processing_with_signature(results)
    test_webhook_error_handling(results)
    test_client_webhook_integration(results)
    test_real_world_webhook_scenarios(results)
    
    # Print final results
    success = results.summary()
    
    if success:
        print("\n🎉 All webhook tests passed! Webhook functionality is fully validated.")
    else:
        print("\n⚠️ Some webhook tests failed. Please check the errors above.")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
