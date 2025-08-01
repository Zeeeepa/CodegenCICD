#!/usr/bin/env python3
"""
Simple Web Evaluation Test for CICD Dashboard
Tests the UI without requiring Selenium/Chrome
"""

import requests
import json
import time
import re
from urllib.parse import urljoin
from typing import Dict, Any, List

class SimpleWebEvaluator:
    def __init__(self, base_url: str = "http://localhost:3001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def test_page_load(self) -> Dict[str, Any]:
        """Test basic page loading"""
        print("🔍 Testing page load...")
        
        try:
            start_time = time.time()
            response = self.session.get(self.base_url, timeout=10)
            load_time = (time.time() - start_time) * 1000
            
            result = {
                "status": "success" if response.status_code == 200 else "failed",
                "status_code": response.status_code,
                "load_time_ms": load_time,
                "content_length": len(response.text),
                "content_type": response.headers.get('content-type', ''),
                "html_content": response.text
            }
            
            print(f"✅ Page loaded: {response.status_code} ({load_time:.1f}ms)")
            return result
            
        except Exception as e:
            print(f"❌ Page load failed: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def analyze_html_content(self, html_content: str) -> Dict[str, Any]:
        """Analyze HTML content for React/UI components"""
        print("🔍 Analyzing HTML content...")
        
        analysis = {
            "has_react_root": bool(re.search(r'<div[^>]*id=["\']root["\']', html_content)),
            "has_title": "CodegenCICD" in html_content or "Dashboard" in html_content,
            "has_material_ui": "Material" in html_content or "mui" in html_content.lower(),
            "has_css_bundles": bool(re.search(r'<link[^>]*\.css', html_content)),
            "has_js_bundles": bool(re.search(r'<script[^>]*\.js', html_content)),
            "has_meta_viewport": bool(re.search(r'<meta[^>]*viewport', html_content)),
            "bundle_count": len(re.findall(r'<script[^>]*src=["\'][^"\']*\.js["\']', html_content)),
            "css_count": len(re.findall(r'<link[^>]*href=["\'][^"\']*\.css["\']', html_content))
        }
        
        # Extract bundle names
        js_bundles = re.findall(r'<script[^>]*src=["\']([^"\']*\.js)["\']', html_content)
        css_bundles = re.findall(r'<link[^>]*href=["\']([^"\']*\.css)["\']', html_content)
        
        analysis["js_bundles"] = js_bundles
        analysis["css_bundles"] = css_bundles
        
        score = sum([
            analysis["has_react_root"],
            analysis["has_title"],
            analysis["has_material_ui"],
            analysis["has_css_bundles"],
            analysis["has_js_bundles"],
            analysis["has_meta_viewport"]
        ])
        
        analysis["ui_score"] = score
        analysis["max_score"] = 6
        analysis["percentage"] = (score / 6) * 100
        
        print(f"✅ HTML analysis complete: {score}/6 checks passed ({analysis['percentage']:.1f}%)")
        return analysis
    
    def test_api_endpoints(self) -> Dict[str, Any]:
        """Test backend API endpoints"""
        print("🔍 Testing API endpoints...")
        
        # Determine backend URL (usually port 8000)
        backend_url = self.base_url.replace(":3001", ":8000").replace(":3000", ":8000")
        
        endpoints = [
            "/health",
            "/api/projects", 
            "/api/github-repos",
            "/api/agent-runs",
            "/metrics"
        ]
        
        results = {}
        total_passed = 0
        
        for endpoint in endpoints:
            try:
                url = urljoin(backend_url, endpoint)
                response = self.session.get(url, timeout=5)
                
                result = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "content_length": len(response.text)
                }
                
                if response.status_code == 200:
                    total_passed += 1
                    print(f"✅ {endpoint}: OK ({result['response_time_ms']:.1f}ms)")
                else:
                    print(f"❌ {endpoint}: {response.status_code}")
                
                results[endpoint] = result
                
            except Exception as e:
                print(f"❌ {endpoint}: {e}")
                results[endpoint] = {
                    "success": False,
                    "error": str(e)
                }
        
        results["summary"] = {
            "total_endpoints": len(endpoints),
            "passed_endpoints": total_passed,
            "success_rate": (total_passed / len(endpoints)) * 100
        }
        
        print(f"✅ API test complete: {total_passed}/{len(endpoints)} endpoints working")
        return results
    
    def test_static_assets(self, html_content: str) -> Dict[str, Any]:
        """Test if static assets load correctly"""
        print("🔍 Testing static assets...")
        
        # Extract asset URLs
        js_bundles = re.findall(r'<script[^>]*src=["\']([^"\']*\.js)["\']', html_content)
        css_bundles = re.findall(r'<link[^>]*href=["\']([^"\']*\.css)["\']', html_content)
        
        results = {
            "js_assets": {},
            "css_assets": {},
            "total_assets": len(js_bundles) + len(css_bundles),
            "loaded_assets": 0
        }
        
        # Test JS bundles
        for bundle in js_bundles:
            if bundle.startswith('/'):
                url = urljoin(self.base_url, bundle)
            else:
                url = bundle
                
            try:
                response = self.session.get(url, timeout=5)
                success = response.status_code == 200
                results["js_assets"][bundle] = {
                    "status_code": response.status_code,
                    "success": success,
                    "size_bytes": len(response.content)
                }
                if success:
                    results["loaded_assets"] += 1
                    print(f"✅ JS: {bundle} ({len(response.content)} bytes)")
                else:
                    print(f"❌ JS: {bundle} - {response.status_code}")
            except Exception as e:
                print(f"❌ JS: {bundle} - {e}")
                results["js_assets"][bundle] = {"success": False, "error": str(e)}
        
        # Test CSS bundles
        for bundle in css_bundles:
            if bundle.startswith('/'):
                url = urljoin(self.base_url, bundle)
            else:
                url = bundle
                
            try:
                response = self.session.get(url, timeout=5)
                success = response.status_code == 200
                results["css_assets"][bundle] = {
                    "status_code": response.status_code,
                    "success": success,
                    "size_bytes": len(response.content)
                }
                if success:
                    results["loaded_assets"] += 1
                    print(f"✅ CSS: {bundle} ({len(response.content)} bytes)")
                else:
                    print(f"❌ CSS: {bundle} - {response.status_code}")
            except Exception as e:
                print(f"❌ CSS: {bundle} - {e}")
                results["css_assets"][bundle] = {"success": False, "error": str(e)}
        
        results["asset_load_rate"] = (results["loaded_assets"] / results["total_assets"]) * 100 if results["total_assets"] > 0 else 0
        print(f"✅ Asset test complete: {results['loaded_assets']}/{results['total_assets']} assets loaded")
        return results
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive web evaluation test"""
        print("🚀 Starting Comprehensive Web Evaluation Test")
        print("=" * 60)
        
        start_time = time.time()
        
        # Test 1: Page Load
        page_result = self.test_page_load()
        if page_result["status"] != "success":
            return {
                "status": "failed",
                "error": "Page load failed",
                "details": page_result
            }
        
        html_content = page_result.get("html_content", "")
        
        # Test 2: HTML Analysis
        html_analysis = self.analyze_html_content(html_content)
        
        # Test 3: API Endpoints
        api_results = self.test_api_endpoints()
        
        # Test 4: Static Assets
        asset_results = self.test_static_assets(html_content)
        
        # Calculate overall score
        ui_score = html_analysis["percentage"]
        api_score = api_results["summary"]["success_rate"]
        asset_score = asset_results["asset_load_rate"]
        
        overall_score = (ui_score + api_score + asset_score) / 3
        
        end_time = time.time()
        
        final_result = {
            "status": "completed",
            "overall_score": overall_score,
            "duration_seconds": end_time - start_time,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "target_url": self.base_url,
            "tests": {
                "page_load": page_result,
                "html_analysis": html_analysis,
                "api_endpoints": api_results,
                "static_assets": asset_results
            },
            "scores": {
                "ui_score": ui_score,
                "api_score": api_score,
                "asset_score": asset_score,
                "overall_score": overall_score
            },
            "recommendations": self.generate_recommendations(ui_score, api_score, asset_score)
        }
        
        return final_result
    
    def generate_recommendations(self, ui_score: float, api_score: float, asset_score: float) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if ui_score < 80:
            recommendations.append("🔧 Improve UI component loading and structure")
        if api_score < 80:
            recommendations.append("🔧 Fix API endpoint issues")
        if asset_score < 80:
            recommendations.append("🔧 Resolve static asset loading problems")
        
        if ui_score >= 90 and api_score >= 90 and asset_score >= 90:
            recommendations.append("✅ Excellent! All systems are working well")
        elif ui_score >= 70 and api_score >= 70 and asset_score >= 70:
            recommendations.append("✅ Good performance with minor improvements needed")
        else:
            recommendations.append("⚠️ Significant issues found that need attention")
        
        return recommendations
    
    def print_report(self, results: Dict[str, Any]) -> None:
        """Print a formatted test report"""
        print("\n" + "=" * 60)
        print("🧪 WEB EVALUATION TEST REPORT")
        print("=" * 60)
        print(f"Target URL: {results['target_url']}")
        print(f"Test Status: {results['status']}")
        print(f"Overall Score: {results['overall_score']:.1f}%")
        print(f"Duration: {results['duration_seconds']:.2f} seconds")
        print(f"Timestamp: {results['timestamp']}")
        
        print("\n📊 DETAILED SCORES:")
        print(f"  UI Components: {results['scores']['ui_score']:.1f}%")
        print(f"  API Endpoints: {results['scores']['api_score']:.1f}%")
        print(f"  Static Assets: {results['scores']['asset_score']:.1f}%")
        
        print("\n💡 RECOMMENDATIONS:")
        for rec in results['recommendations']:
            print(f"  {rec}")
        
        print("\n🔍 DETAILED RESULTS:")
        
        # Page Load
        page_load = results['tests']['page_load']
        print(f"  Page Load: {page_load['status_code']} ({page_load.get('load_time_ms', 0):.1f}ms)")
        
        # HTML Analysis
        html = results['tests']['html_analysis']
        print(f"  HTML Analysis: {html['ui_score']}/{html['max_score']} checks passed")
        print(f"    - React Root: {'✅' if html['has_react_root'] else '❌'}")
        print(f"    - Dashboard Title: {'✅' if html['has_title'] else '❌'}")
        print(f"    - Material-UI: {'✅' if html['has_material_ui'] else '❌'}")
        print(f"    - CSS Bundles: {'✅' if html['has_css_bundles'] else '❌'}")
        print(f"    - JS Bundles: {'✅' if html['has_js_bundles'] else '❌'}")
        print(f"    - Viewport Meta: {'✅' if html['has_meta_viewport'] else '❌'}")
        
        # API Endpoints
        api = results['tests']['api_endpoints']['summary']
        print(f"  API Endpoints: {api['passed_endpoints']}/{api['total_endpoints']} working")
        
        # Static Assets
        assets = results['tests']['static_assets']
        print(f"  Static Assets: {assets['loaded_assets']}/{assets['total_assets']} loaded")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple Web Evaluation Test")
    parser.add_argument("--url", default="http://localhost:3001", help="Target URL to test")
    
    args = parser.parse_args()
    
    evaluator = SimpleWebEvaluator(args.url)
    results = evaluator.run_comprehensive_test()
    
    # Print report
    evaluator.print_report(results)
    
    # Save results
    with open("simple_web_eval_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: simple_web_eval_results.json")
    
    # Return appropriate exit code
    overall_score = results.get("overall_score", 0)
    return 0 if overall_score >= 70 else 1

if __name__ == "__main__":
    exit(main())

