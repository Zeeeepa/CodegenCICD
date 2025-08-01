#!/usr/bin/env python3
"""
Run comprehensive tests on the CodegenCICD dashboard using Web-Eval-Agent
"""
import asyncio
import json
import httpx
import time
from datetime import datetime

async def run_tests():
    """Run comprehensive tests"""
    
    # Test payload
    test_payload = {
        "base_url": "http://localhost:8000",
        "gemini_api_key": "AIzaSyBXmhlHudrD4zXiv-5fjxi1gGG-_kdtaZ0",
        "scenarios": [
            {
                "name": "Homepage Load Test",
                "description": "Test dashboard homepage loading and basic elements",
                "actions": [
                    {"type": "navigate", "url": "http://localhost:8000"},
                    {"type": "wait", "selector": "[data-testid='dashboard-header']", "timeout": 10},
                    {"type": "check_element", "selector": "h1", "expected_text": "CodegenCICD Dashboard"},
                    {"type": "screenshot", "name": "homepage_loaded"}
                ]
            },
            {
                "name": "Project Selector Test",
                "description": "Test GitHub project selector dropdown functionality",
                "actions": [
                    {"type": "navigate", "url": "http://localhost:8000"},
                    {"type": "wait", "selector": "[data-testid='project-selector']", "timeout": 10},
                    {"type": "click", "selector": "[data-testid='project-selector']"},
                    {"type": "screenshot", "name": "project_selector_open"}
                ]
            }
        ],
        "browser_config": {
            "headless": True,
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "CodegenCICD-Test-Agent/1.0"
        }
    }
    
    try:
        print("🚀 Starting comprehensive dashboard tests...")
        print(f"📊 Dashboard URL: {test_payload['base_url']}")
        print(f"🤖 Web-Eval-Agent URL: http://localhost:8003")
        
        async with httpx.AsyncClient(timeout=300) as client:
            # First check if Web-Eval-Agent is healthy
            health_response = await client.get("http://localhost:8003/health")
            print(f"✅ Web-Eval-Agent Health: {health_response.json()}")
            
            # Run comprehensive tests
            print("\n🧪 Running comprehensive test suite...")
            response = await client.post(
                "http://localhost:8003/api/test/comprehensive",
                json=test_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                results = response.json()
                
                print("\n📋 TEST RESULTS SUMMARY")
                print("=" * 50)
                print(f"Overall Status: {results.get('overall_status', 'unknown').upper()}")
                print(f"Total Scenarios: {results.get('total_scenarios', 0)}")
                print(f"Passed: {results.get('passed_scenarios', 0)}")
                print(f"Partial: {results.get('partial_scenarios', 0)}")
                print(f"Failed: {results.get('failed_scenarios', 0)}")
                
                if 'summary' in results:
                    print("\n🔍 DETAILED SUMMARY")
                    print("-" * 30)
                    summary = results['summary']
                    for key, value in summary.items():
                        status = "✅" if value else "❌"
                        print(f"{status} {key.replace('_', ' ').title()}: {value}")
                
                if 'results' in results:
                    print("\n📝 INDIVIDUAL TEST RESULTS")
                    print("-" * 40)
                    for i, result in enumerate(results['results'], 1):
                        status_icon = "✅" if result.get('status') == 'passed' else "⚠️" if result.get('status') == 'partial' else "❌"
                        print(f"{status_icon} {i}. {result.get('name', 'Unknown Test')}")
                        print(f"   Status: {result.get('status', 'unknown').upper()}")
                        print(f"   Message: {result.get('message', 'No message')}")
                        if result.get('error'):
                            print(f"   Error: {result['error']}")
                        print()
                
                # Save results to file
                with open("test_results.json", "w") as f:
                    json.dump(results, f, indent=2, default=str)
                
                print(f"💾 Full results saved to: test_results.json")
                
                return results
                
            else:
                print(f"❌ Test execution failed: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        return None

async def test_individual_components():
    """Test individual components"""
    print("\n🔧 Testing Individual Components...")
    
    components = [
        {
            "name": "Dashboard Component",
            "url": "http://localhost:8000",
            "component": "dashboard",
            "checks": ["header_present", "project_selector_visible", "navigation_functional"]
        },
        {
            "name": "Project Cards",
            "url": "http://localhost:8000",
            "component": "project_cards", 
            "checks": ["cards_render", "run_button_functional", "settings_button_functional"]
        }
    ]
    
    results = {}
    
    async with httpx.AsyncClient(timeout=60) as client:
        for component in components:
            try:
                print(f"🧪 Testing {component['name']}...")
                
                test_payload = {
                    "url": component["url"],
                    "gemini_api_key": "AIzaSyBXmhlHudrD4zXiv-5fjxi1gGG-_kdtaZ0",
                    "test_type": "component",
                    "component": component["component"],
                    "checks": component["checks"]
                }
                
                response = await client.post(
                    "http://localhost:8003/api/test/component",
                    json=test_payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    results[component["name"]] = result
                    
                    status_icon = "✅" if result.get('status') == 'passed' else "❌"
                    print(f"{status_icon} {component['name']}: {result.get('status', 'unknown').upper()}")
                    print(f"   Details: {result.get('details', 'No details')}")
                else:
                    print(f"❌ {component['name']}: HTTP {response.status_code}")
                    results[component["name"]] = {"status": "failed", "error": response.text}
                    
            except Exception as e:
                print(f"❌ {component['name']}: {str(e)}")
                results[component["name"]] = {"status": "failed", "error": str(e)}
    
    return results

async def main():
    """Main test execution"""
    print("🎯 CodegenCICD Dashboard - Web-Eval-Agent Testing")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now().isoformat()}")
    
    # Run comprehensive tests
    comprehensive_results = await run_tests()
    
    # Run component tests
    component_results = await test_individual_components()
    
    # Generate final report
    print("\n📊 FINAL TEST REPORT")
    print("=" * 60)
    
    if comprehensive_results:
        overall_status = comprehensive_results.get('overall_status', 'unknown')
        print(f"🎯 Overall Status: {overall_status.upper()}")
        
        if overall_status == 'passed':
            print("🎉 All tests passed! The dashboard is working correctly.")
        elif overall_status == 'partial':
            print("⚠️ Some tests passed with warnings. Review the details above.")
        else:
            print("❌ Tests failed. Please review the errors above.")
    else:
        print("❌ Comprehensive tests could not be completed.")
    
    print(f"\n⏰ Completed at: {datetime.now().isoformat()}")
    
    # Save combined results
    final_results = {
        "comprehensive": comprehensive_results,
        "components": component_results,
        "timestamp": datetime.now().isoformat()
    }
    
    with open("final_test_results.json", "w") as f:
        json.dump(final_results, f, indent=2, default=str)
    
    print(f"💾 Final results saved to: final_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
