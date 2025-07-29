#!/usr/bin/env python3
"""
Test script for the upgraded Codegen API client
"""
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """Test that all new modules can be imported"""
    try:
        # Test individual module imports
        from integrations.codegen_config import ClientConfig, ConfigPresets
        print("✅ Config module imported successfully")
        
        from integrations.codegen_api_models import (
            SourceType, MessageType, AgentRunStatus,
            UserResponse, AgentRunResponse
        )
        print("✅ API models imported successfully")
        
        from integrations.codegen_exceptions import (
            ValidationError, CodegenAPIError, RateLimitError
        )
        print("✅ Exceptions imported successfully")
        
        # Test that enums have the expected values
        assert MessageType.ACTION.value == "ACTION"
        assert MessageType.PLAN_EVALUATION.value == "PLAN_EVALUATION"
        assert MessageType.INITIAL_PR_GENERATION.value == "INITIAL_PR_GENERATION"
        assert AgentRunStatus.PAUSED.value == "paused"
        print("✅ Enums have correct values")
        
        # Test configuration
        config = ConfigPresets.development()
        assert config.log_level == "DEBUG"
        assert config.timeout == 60
        print("✅ Configuration presets work correctly")
        
        print("\n🎉 All imports and basic functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_client_creation():
    """Test client creation with mock credentials"""
    try:
        # Set mock environment variables
        os.environ['CODEGEN_API_TOKEN'] = 'test-token'
        os.environ['CODEGEN_ORG_ID'] = '123'
        
        from integrations.codegen_client import CodegenClient
        from integrations.codegen_config import ClientConfig
        
        # Test with default config
        config = ClientConfig()
        assert config.api_token == 'test-token'
        assert config.org_id == '123'
        print("✅ Configuration loads from environment variables")
        
        # Test client creation (without making actual requests)
        client = CodegenClient(config)
        assert client.config.api_token == 'test-token'
        assert client.session is not None
        assert client.rate_limiter is not None
        print("✅ Client created successfully with all components")
        
        # Test context manager
        with CodegenClient(config) as client:
            assert client.session is not None
        print("✅ Context manager works correctly")
        
        print("\n🎉 Client creation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Client creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Testing upgraded Codegen API client...\n")
    
    success = True
    success &= test_imports()
    success &= test_client_creation()
    
    if success:
        print("\n✅ All tests passed! The client upgrade is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)
