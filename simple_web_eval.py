#!/usr/bin/env python3
"""
Simple Web Evaluation Script
Tests the CodegenCICD UI and API without browser dependencies
"""

import requests
import json
from bs4 import BeautifulSoup

def test_api_endpoints():
    """Test API endpoints directly"""
    print("🔧 Testing API Endpoints...")
    
    endpoints = [
        "/health",
        "/api/projects", 
        "/api/system/status",
        "/api/agents/runs",
        "/api/config"
    ]
    
    results = {}
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"http://localhost:8000{endpoint}", timeout=5)
            results[endpoint] = {
                'status': response.status_code,
                'success': response.status_code == 200
            }
            
            print(f"✅ {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    results[endpoint]['data'] = data
                    print(f"   📊 Response: {json.dumps(data, indent=2)[:200]}...")
                except:
                    results[endpoint]['data'] = response.text[:200]
                    print(f"   📄 Response: {response.text[:100]}...")
            else:
                results[endpoint]['error'] = response.text[:200]
                
        except Exception as e:
            results[endpoint] = {
                'status': 'error',
                'success': False,
                'error': str(e)
            }
            print(f"❌ {endpoint}: {e}")
    
    return results

def test_frontend():
    """Test frontend UI"""
    print("\n🌐 Testing Frontend UI...")
    
    try:
        response = requests.get("http://localhost:3001", timeout=10)
        print(f"✅ Frontend Status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract key information
            title = soup.find('title')
            print(f"📄 Page Title: {title.text if title else 'No title found'}")
            
            # Look for React app
            root_div = soup.find('div', {'id': 'root'})
            if root_div:
                print("✅ React app root found")
            else:
                print("❌ React app root not found")
            
            # Look for meta tags
            meta_description = soup.find('meta', {'name': 'description'})
            if meta_description:
                print(f"📝 Description: {meta_description.get('content', 'No content')}")
            
            # Look for scripts (React bundles)
            scripts = soup.find_all('script', src=True)
            react_scripts = [s for s in scripts if 'static/js' in s.get('src', '')]
            print(f"📦 Found {len(react_scripts)} React bundle scripts")
            
            # Look for stylesheets
            stylesheets = soup.find_all('link', rel='stylesheet')
            print(f"🎨 Found {len(stylesheets)} stylesheets")
            
            return {
                'status': response.status_code,
                'success': True,
                'title': title.text if title else None,
                'has_react_root': bool(root_div),
                'script_count': len(react_scripts),
                'stylesheet_count': len(stylesheets)
            }
        else:
            return {
                'status': response.status_code,
                'success': False,
                'error': response.text[:200]
            }
            
    except Exception as e:
        print(f"❌ Frontend test failed: {e}")
        return {
            'status': 'error',
            'success': False,
            'error': str(e)
        }

def test_integration():
    """Test integration between frontend and backend"""
    print("\n🔗 Testing Frontend-Backend Integration...")
    
    # Test if frontend can reach backend
    try:
        # This simulates what the frontend would do
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Test CORS and basic connectivity
        response = requests.options("http://localhost:8000/api/projects", headers=headers, timeout=5)
        print(f"✅ CORS preflight: {response.status_code}")
        
        # Test actual API call that frontend would make
        response = requests.get("http://localhost:8000/api/projects", headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Projects API: Found {len(data.get('projects', []))} projects")
            return True
        else:
            print(f"❌ Projects API failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def generate_report(api_results, frontend_results, integration_success):
    """Generate a comprehensive report"""
    print("\n" + "="*60)
    print("📊 CODEGENCD SYSTEM EVALUATION REPORT")
    print("="*60)
    
    # API Status
    print("\n🔧 API ENDPOINTS STATUS:")
    api_success_count = sum(1 for r in api_results.values() if r.get('success', False))
    print(f"   ✅ Successful: {api_success_count}/{len(api_results)}")
    
    for endpoint, result in api_results.items():
        status = "✅" if result.get('success', False) else "❌"
        print(f"   {status} {endpoint}: {result.get('status', 'unknown')}")
    
    # Frontend Status
    print(f"\n🌐 FRONTEND STATUS:")
    if frontend_results.get('success', False):
        print(f"   ✅ Status: {frontend_results['status']}")
        print(f"   📄 Title: {frontend_results.get('title', 'Unknown')}")
        print(f"   ⚛️ React App: {'Yes' if frontend_results.get('has_react_root') else 'No'}")
        print(f"   📦 Scripts: {frontend_results.get('script_count', 0)}")
        print(f"   🎨 Stylesheets: {frontend_results.get('stylesheet_count', 0)}")
    else:
        print(f"   ❌ Status: {frontend_results.get('status', 'error')}")
        print(f"   ❌ Error: {frontend_results.get('error', 'Unknown error')}")
    
    # Integration Status
    print(f"\n🔗 INTEGRATION STATUS:")
    print(f"   {'✅' if integration_success else '❌'} Frontend-Backend Communication: {'Working' if integration_success else 'Failed'}")
    
    # Overall Status
    overall_success = (
        api_success_count >= len(api_results) * 0.8 and  # 80% of APIs working
        frontend_results.get('success', False) and
        integration_success
    )
    
    print(f"\n🎯 OVERALL SYSTEM STATUS:")
    print(f"   {'🟢 HEALTHY' if overall_success else '🔴 ISSUES DETECTED'}")
    
    if overall_success:
        print("\n🎉 System is ready for use!")
        print("   - Backend API is responding correctly")
        print("   - Frontend is loading properly")
        print("   - Integration between services is working")
        print("\n🌐 Access the dashboard at: http://localhost:3001")
        print("🔧 API documentation at: http://localhost:8000/docs")
    else:
        print("\n⚠️ System has issues that need attention:")
        if api_success_count < len(api_results) * 0.8:
            print("   - Some API endpoints are not responding")
        if not frontend_results.get('success', False):
            print("   - Frontend is not loading correctly")
        if not integration_success:
            print("   - Frontend cannot communicate with backend")

if __name__ == "__main__":
    print("🎯 CodegenCICD System Evaluation")
    print("=" * 50)
    
    # Run all tests
    api_results = test_api_endpoints()
    frontend_results = test_frontend()
    integration_success = test_integration()
    
    # Generate comprehensive report
    generate_report(api_results, frontend_results, integration_success)
    
    print("\n✨ Evaluation Complete!")

