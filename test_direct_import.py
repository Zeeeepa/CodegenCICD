#!/usr/bin/env python3
"""
Direct test of the new Codegen client modules
"""
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_direct_imports():
    """Test direct imports of new modules"""
    try:
        # Set mock environment variables
        os.environ['CODEGEN_API_TOKEN'] = 'test-token'
        os.environ['CODEGEN_ORG_ID'] = '123'
        
        # Test direct imports
        from integrations.codegen_config import ClientConfig, ConfigPresets
        from integrations.codegen_api_models import MessageType, AgentRunStatus
        from integrations.codegen_exceptions import ValidationError
        from integrations.codegen_client import CodegenClient
        
        print("✅ All modules imported successfully")
        
        # Test enum values
        assert MessageType.ACTION.value == "ACTION"
        assert MessageType.INITIAL_PR_GENERATION.value == "INITIAL_PR_GENERATION"
        assert AgentRunStatus.PAUSED.value == "paused"
        print("✅ Enums have correct values")
        
        # Test configuration
        config = ConfigPresets.development()
        assert config.log_level == "DEBUG"
        print("✅ Configuration presets work")
        
        # Test client creation
        client = CodegenClient(config)
        assert client.config.api_token == 'test-token'
        print("✅ Client created successfully")
        
        # Test validation
        try:
            client._validate_pagination(-1, 50)
            assert False, "Should have raised ValidationError"
        except ValidationError:
            print("✅ Validation works correctly")
        
        client.close()
        print("✅ Client cleanup works")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Testing direct imports of upgraded Codegen client...\n")
    
    if test_direct_imports():
        print("\n🎉 All direct import tests passed! The upgrade is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Tests failed.")
        sys.exit(1)
