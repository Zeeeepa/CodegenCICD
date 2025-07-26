#!/usr/bin/env python3
"""
System integration test for CodegenCICD Dashboard
Tests the core functionality without exposing sensitive data
"""
import os
import asyncio
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_codegen_api():
    """Test Codegen API connection"""
    print("🤖 Testing Codegen API...")
    
    org_id = os.getenv("CODEGEN_ORG_ID")
    api_token = os.getenv("CODEGEN_API_TOKEN")
    
    if not org_id or not api_token:
        print("❌ Missing Codegen API credentials")
        return False
    
    try:
        url = f"https://api.codegen.com/v1/organizations/{org_id}/agent/run"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": "Test CodegenCICD Dashboard integration",
            "metadata": {"source": "codegencd_test"}
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✅ Codegen API working! Agent Run ID: {data.get('id')}")
            return True
        else:
            print(f"❌ Codegen API error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Codegen API test failed: {e}")
        return False

def test_gemini_api():
    """Test Gemini API connection"""
    print("\n🧠 Testing Gemini AI...")
    
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ Missing Gemini API key")
        return False
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": "Test validation: Is 'Server started successfully' a success? Reply with SUCCESS or FAILURE."
                }]
            }]
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            print("✅ Gemini AI working!")
            return True
        else:
            print(f"❌ Gemini API error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Gemini API test failed: {e}")
        return False

def test_cloudflare_worker():
    """Test Cloudflare Worker"""
    print("\n☁️ Testing Cloudflare Worker...")
    
    worker_url = os.getenv("CLOUDFLARE_WORKER_URL")
    
    if not worker_url:
        print("❌ Missing Cloudflare Worker URL")
        return False
    
    try:
        response = requests.get(worker_url)
        
        if response.status_code in [200, 404, 405]:
            print("✅ Cloudflare Worker accessible!")
            return True
        else:
            print(f"❌ Cloudflare Worker error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Cloudflare Worker test failed: {e}")
        return False

def main():
    """Run system integration tests"""
    print("🚀 CodegenCICD Dashboard System Tests")
    print("=" * 50)
    
    results = []
    
    # Test core integrations
    results.append(("Codegen API", test_codegen_api()))
    results.append(("Gemini AI", test_gemini_api()))
    results.append(("Cloudflare Worker", test_cloudflare_worker()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed >= 2:
        print("🎉 Core integrations working! System ready for implementation.")
        return True
    else:
        print("⚠️ Some integrations failed. Check configuration.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
