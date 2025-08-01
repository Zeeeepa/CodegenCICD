#!/usr/bin/env python3
"""
Web Evaluation Agent Test Script
Visits the CodegenCICD UI and fetches contents
"""

import asyncio
import json
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import requests

async def test_ui_with_playwright():
    """Test the UI using Playwright to simulate web-eval-agent behavior"""
    
    print("🚀 Starting Web Evaluation Agent Test...")
    
    # First, check if services are running
    try:
        backend_response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"✅ Backend Status: {backend_response.json()}")
    except Exception as e:
        print(f"❌ Backend not accessible: {e}")
        return
    
    try:
        frontend_response = requests.get("http://localhost:3001", timeout=5)
        print(f"✅ Frontend Status: {frontend_response.status_code}")
    except Exception as e:
        print(f"❌ Frontend not accessible: {e}")
        return
    
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("\n🌐 Navigating to CodegenCICD Dashboard...")
            await page.goto("http://localhost:3001", wait_until="networkidle")
            
            # Wait for the page to load
            await page.wait_for_timeout(3000)
            
            # Get page title
            title = await page.title()
            print(f"📄 Page Title: {title}")
            
            # Get page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract key information
            print("\n📊 Dashboard Analysis:")
            
            # Look for main components
            main_content = soup.find('div', {'id': 'root'})
            if main_content:
                print("✅ React app root found")
                
                # Look for dashboard components
                dashboard_elements = soup.find_all(['div', 'section', 'main'], class_=lambda x: x and ('dashboard' in x.lower() or 'main' in x.lower()))
                print(f"📋 Found {len(dashboard_elements)} dashboard-related elements")
                
                # Look for navigation
                nav_elements = soup.find_all(['nav', 'div'], class_=lambda x: x and ('nav' in x.lower() or 'menu' in x.lower()))
                print(f"🧭 Found {len(nav_elements)} navigation elements")
                
                # Look for cards/components
                card_elements = soup.find_all(['div'], class_=lambda x: x and 'card' in x.lower())
                print(f"🃏 Found {len(card_elements)} card components")
                
                # Extract text content (first 500 chars)
                text_content = main_content.get_text(strip=True)[:500]
                print(f"📝 Page Content Preview: {text_content}...")
            
            # Take a screenshot
            await page.screenshot(path="dashboard_screenshot.png")
            print("📸 Screenshot saved as dashboard_screenshot.png")
            
            # Test API endpoints through the UI
            print("\n🔌 Testing API Integration...")
            
            # Check if there are any API calls being made
            api_responses = []
            
            def handle_response(response):
                if 'localhost:8000' in response.url:
                    api_responses.append({
                        'url': response.url,
                        'status': response.status,
                        'method': response.request.method
                    })
            
            page.on('response', handle_response)
            
            # Trigger some interactions to test API calls
            try:
                # Look for buttons or interactive elements
                buttons = await page.query_selector_all('button')
                print(f"🔘 Found {len(buttons)} buttons")
                
                if buttons:
                    # Click the first button to test interaction
                    await buttons[0].click()
                    await page.wait_for_timeout(2000)
                    
            except Exception as e:
                print(f"⚠️ Interaction test failed: {e}")
            
            if api_responses:
                print("📡 API Calls Detected:")
                for response in api_responses:
                    print(f"  - {response['method']} {response['url']} -> {response['status']}")
            else:
                print("📡 No API calls detected during interaction")
            
            # Test specific dashboard features
            print("\n🎯 Testing Dashboard Features...")
            
            # Look for project-related elements
            project_elements = await page.query_selector_all('[data-testid*="project"], [class*="project"], [id*="project"]')
            print(f"📁 Found {len(project_elements)} project-related elements")
            
            # Look for CI/CD related elements
            cicd_elements = await page.query_selector_all('[data-testid*="cicd"], [class*="cicd"], [id*="cicd"], [class*="pipeline"]')
            print(f"⚙️ Found {len(cicd_elements)} CI/CD-related elements")
            
            # Check for loading states
            loading_elements = await page.query_selector_all('[class*="loading"], [class*="spinner"]')
            print(f"⏳ Found {len(loading_elements)} loading indicators")
            
            print("\n✅ Web Evaluation Complete!")
            
        except Exception as e:
            print(f"❌ Error during evaluation: {e}")
            
        finally:
            await browser.close()

def test_api_endpoints():
    """Test API endpoints directly"""
    print("\n🔧 Testing API Endpoints Directly...")
    
    endpoints = [
        "/health",
        "/api/projects",
        "/api/agents",
        "/api/system/status"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"http://localhost:8000{endpoint}", timeout=5)
            print(f"✅ {endpoint}: {response.status_code}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   📊 Response: {json.dumps(data, indent=2)[:200]}...")
                except:
                    print(f"   📄 Response: {response.text[:100]}...")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")

if __name__ == "__main__":
    print("🎯 CodegenCICD Web Evaluation Agent Test")
    print("=" * 50)
    
    # Test API endpoints first
    test_api_endpoints()
    
    # Then test UI with Playwright
    asyncio.run(test_ui_with_playwright())
    
    print("\n🎉 Evaluation Complete!")

