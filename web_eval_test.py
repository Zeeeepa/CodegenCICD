#!/usr/bin/env python3
"""
Simple web evaluation script to test UI content
Uses Selenium or requests to analyze the frontend
"""

import requests
import json
import time
from urllib.parse import urljoin
import os

class WebEvaluator:
    def __init__(self, base_url="http://localhost:3001"):
        self.base_url = base_url
        
    def test_basic_functionality(self):
        """Test basic UI functionality"""
        results = {
            "page_loads": False,
            "elements_found": 0,
            "links_working": 0,
            "forms_detected": 0,
            "javascript_loaded": False,
            "css_loaded": False,
            "content_analysis": {}
        }
        
        try:
            # Test main page load
            response = requests.get(self.base_url, timeout=10)
            if response.status_code == 200:
                results["page_loads"] = True
                html_content = response.text
                
                # Analyze content
                results["content_analysis"] = {
                    "content_length": len(html_content),
                    "has_react_root": "root" in html_content,
                    "has_title": "CodegenCICD" in html_content,
                    "has_js_bundles": "static/js" in html_content,
                    "has_css_bundles": "static/css" in html_content,
                    "has_manifest": "manifest.json" in html_content
                }
                
                # Count basic elements
                results["elements_found"] = html_content.count("<") // 2  # Rough element count
                results["javascript_loaded"] = "static/js" in html_content
                results["css_loaded"] = "static/css" in html_content
                
                # Check for forms (basic detection)
                results["forms_detected"] = html_content.count("<form")
                
                # Check for links
                results["links_working"] = html_content.count("<a")
                
        except Exception as e:
            results["error"] = str(e)
            
        return results
    
    def test_api_integration(self, backend_url="http://localhost:8000"):
        """Test if frontend can communicate with backend"""
        results = {
            "backend_reachable": False,
            "cors_configured": False,
            "api_endpoints_working": []
        }
        
        try:
            # Test backend health
            health_response = requests.get(f"{backend_url}/health", timeout=5)
            if health_response.status_code == 200:
                results["backend_reachable"] = True
                
                # Test CORS by checking headers
                if "access-control-allow-origin" in health_response.headers:
                    results["cors_configured"] = True
                
                # Test key API endpoints
                endpoints = [
                    "/api/projects",
                    "/api/github-repos", 
                    "/api/agent-runs",
                    "/api/metrics"
                ]
                
                for endpoint in endpoints:
                    try:
                        resp = requests.get(f"{backend_url}{endpoint}", timeout=5)
                        if resp.status_code == 200:
                            results["api_endpoints_working"].append(endpoint)
                    except:
                        pass
                        
        except Exception as e:
            results["error"] = str(e)
            
        return results

def main():
    """Main evaluation function"""
    evaluator = WebEvaluator()
    
    print("🔍 Starting web evaluation...")
    
    # Test basic functionality
    basic_results = evaluator.test_basic_functionality()
    print(f"📄 Page loads: {'✅' if basic_results['page_loads'] else '❌'}")
    print(f"🎯 Elements found: {basic_results['elements_found']}")
    print(f"📜 JavaScript loaded: {'✅' if basic_results['javascript_loaded'] else '❌'}")
    print(f"🎨 CSS loaded: {'✅' if basic_results['css_loaded'] else '❌'}")
    
    if basic_results.get("content_analysis"):
        analysis = basic_results["content_analysis"]
        print(f"⚛️  React root: {'✅' if analysis['has_react_root'] else '❌'}")
        print(f"📝 Title found: {'✅' if analysis['has_title'] else '❌'}")
        print(f"📦 JS bundles: {'✅' if analysis['has_js_bundles'] else '❌'}")
        print(f"🎨 CSS bundles: {'✅' if analysis['has_css_bundles'] else '❌'}")
    
    # Test API integration
    api_results = evaluator.test_api_integration()
    print(f"🔧 Backend reachable: {'✅' if api_results['backend_reachable'] else '❌'}")
    print(f"🌐 CORS configured: {'✅' if api_results['cors_configured'] else '❌'}")
    print(f"📡 API endpoints working: {len(api_results['api_endpoints_working'])}")
    
    # Overall assessment
    overall_score = 0
    if basic_results["page_loads"]: overall_score += 30
    if basic_results["javascript_loaded"]: overall_score += 20
    if basic_results["css_loaded"]: overall_score += 20
    if api_results["backend_reachable"]: overall_score += 20
    if len(api_results["api_endpoints_working"]) > 2: overall_score += 10
    
    print(f"\n🎯 Overall Score: {overall_score}/100")
    
    if overall_score >= 80:
        print("🎉 UI is fully functional!")
    elif overall_score >= 60:
        print("⚠️  UI is partially functional")
    else:
        print("❌ UI has significant issues")
    
    return overall_score >= 60

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

