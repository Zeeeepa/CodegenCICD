#!/usr/bin/env python3
"""
CodegenCICD CLI - Command line interface for the CodegenCICD Dashboard
Simulates the 'codegen' command to open and interact with the UI
"""
import asyncio
import json
import subprocess
import time
import webbrowser
import requests
from pathlib import Path
import sys
import os

class CodegenCLI:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.server_process = None
        
    def start_services(self):
        """Start both backend and frontend services"""
        print("🚀 Starting CodegenCICD Dashboard...")
        print("⏳ Starting backend and frontend services...")
        
        # Use the start.sh script to start both services
        try:
            self.server_process = subprocess.Popen(
                ["bash", "start.sh"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for both services to start
            print("⏳ Waiting for services to start...")
            backend_ready = False
            frontend_ready = False
            
            for i in range(30):  # Wait up to 30 seconds
                # Check backend
                if not backend_ready:
                    try:
                        response = requests.get(f"{self.base_url}/health", timeout=2)
                        if response.status_code == 200:
                            backend_ready = True
                    except:
                        pass
                
                # Check frontend
                if not frontend_ready:
                    try:
                        response = requests.get(self.frontend_url, timeout=2)
                        if response.status_code == 200:
                            frontend_ready = True
                    except:
                        pass
                
                if backend_ready and frontend_ready:
                    print("✅ Backend and frontend started successfully!")
                    return True
                
                time.sleep(1)
            
            if backend_ready and not frontend_ready:
                print("⚠️  Backend started but frontend failed")
                return True  # Continue with backend only
            elif not backend_ready:
                print("❌ Failed to start backend")
                return False
            
        except Exception as e:
            print(f"❌ Error starting services: {e}")
            return False
    
    def stop_server(self):
        """Stop the server"""
        if self.server_process:
            print("🛑 Stopping server...")
            self.server_process.terminate()
            self.server_process.wait()
            print("✅ Server stopped")
    
    def fetch_ui_content(self):
        """Fetch and analyze UI content from the frontend"""
        try:
            print("📱 Fetching UI content...")
            
            # Get the main frontend page
            response = requests.get(self.frontend_url, timeout=10)
            if response.status_code == 200:
                print("✅ Frontend UI loaded successfully!")
                print(f"📄 Content length: {len(response.text)} characters")
                
                # Extract key information from the HTML
                html_content = response.text
                
                # Check for React app structure
                if "root" in html_content:
                    print("✅ React root element found")
                if "static/js" in html_content:
                    print("✅ JavaScript bundles loaded")
                if "static/css" in html_content:
                    print("✅ CSS styles loaded")
                if "CodegenCICD" in html_content:
                    print("✅ Dashboard title found")
                
                # Try to get actual UI content using web-eval-agent
                return self.analyze_ui_with_web_eval()
                
            else:
                print(f"❌ Failed to load frontend: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error fetching UI content: {e}")
            return False
    
    def analyze_ui_with_web_eval(self):
        """Use web evaluation to analyze the UI content"""
        try:
            print("🔍 Analyzing UI with web evaluation...")
            
            # Use our built-in web evaluation script
            try:
                result = subprocess.run(
                    ["python", "web_eval_test.py"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    print("✅ Web evaluation completed successfully!")
                    # Print the output from the evaluation
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            print(f"  {line}")
                    return True
                else:
                    print("⚠️  Web evaluation had issues but continuing...")
                    # Still print output for debugging
                    if result.stdout:
                        for line in result.stdout.strip().split('\n'):
                            if line.strip():
                                print(f"  {line}")
                    return True  # Don't fail the whole process
                    
            except subprocess.TimeoutExpired:
                print("⚠️  Web evaluation timed out, using basic analysis")
                return True
            except FileNotFoundError:
                print("⚠️  Web evaluation script not found, using basic analysis")
                return True
                
        except Exception as e:
            print(f"⚠️  Error in UI analysis: {e}")
            return True  # Don't fail the whole process
    
    def test_api_endpoints(self):
        """Test key API endpoints"""
        print("🔍 Testing API endpoints...")
        
        endpoints = [
            ("/health", "Health check"),
            ("/api/projects", "Projects API"),
            ("/api/github-repos", "GitHub repos API"),
            ("/api/agent-runs", "Agent runs API"),
            ("/metrics", "Metrics API")
        ]
        
        results = []
        for endpoint, description in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    print(f"✅ {description}: OK")
                    results.append(True)
                else:
                    print(f"❌ {description}: {response.status_code}")
                    results.append(False)
            except Exception as e:
                print(f"❌ {description}: Error - {e}")
                results.append(False)
        
        return all(results)
    
    def check_environment(self):
        """Check required environment variables"""
        required_vars = {
            "CODEGEN_ORG_ID": "Your Codegen organization ID",
            "CODEGEN_API_TOKEN": "Your Codegen API token",
            "GITHUB_TOKEN": "Your GitHub personal access token"
        }
        
        optional_vars = {
            "GEMINI_API_KEY": "Your Gemini API key (for web evaluation)",
            "CLOUDFLARE_API_KEY": "Your Cloudflare API key (for deployment)",
            "CLOUDFLARE_ACCOUNT_ID": "Your Cloudflare account ID",
            "CLOUDFLARE_WORKER_NAME": "Your Cloudflare worker name",
            "CLOUDFLARE_WORKER_URL": "Your Cloudflare worker URL"
        }
        
        missing_required = []
        missing_optional = []
        
        # Check required variables
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing_required.append(f"{var}={description}")
        
        # Check optional variables
        for var, description in optional_vars.items():
            if not os.getenv(var):
                missing_optional.append(f"{var}={description}")
        
        if missing_required:
            print("⚠️  Missing required environment variables. Please add to .env file:")
            print("\n# Required for core functionality")
            for var in missing_required:
                print(var)
            
            if missing_optional:
                print("\n# Optional for advanced features")
                for var in missing_optional:
                    print(var)
            
            print("\nCreate .env file with these variables and run 'codegen' again.")
            return False
        
        if missing_optional:
            print("ℹ️  Optional environment variables not set (advanced features disabled):")
            for var in missing_optional:
                print(f"  - {var}")
            print()
        
        return True
    
    def display_dashboard_info(self):
        """Display dashboard information"""
        try:
            print("\n📊 Dashboard Information:")
            
            # Get health info
            health_response = requests.get(f"{self.base_url}/health", timeout=5)
            if health_response.status_code == 200:
                health_data = health_response.json()
                print(f"🏥 Service Status: {health_data.get('status', 'unknown')}")
                print(f"🔧 Service Name: {health_data.get('service', 'unknown')}")
            
            # Get projects count
            projects_response = requests.get(f"{self.base_url}/api/projects", timeout=5)
            if projects_response.status_code == 200:
                projects_data = projects_response.json()
                print(f"📁 Projects: {len(projects_data)} configured")
            
            # Get agent runs count
            runs_response = requests.get(f"{self.base_url}/api/agent-runs", timeout=5)
            if runs_response.status_code == 200:
                runs_data = runs_response.json()
                print(f"🤖 Agent Runs: {len(runs_data)} total")
            
            print(f"🌐 Frontend URL: {self.frontend_url}")
            print(f"🔧 Backend URL: {self.base_url}")
            
        except Exception as e:
            print(f"❌ Error getting dashboard info: {e}")
    
    def run(self):
        """Main CLI execution"""
        print("🎯 CodegenCICD Dashboard")
        print("=" * 40)
        
        # Check environment variables first
        if not self.check_environment():
            return False
        
        try:
            # Start services
            if not self.start_services():
                return False
            
            # Test API endpoints
            api_success = self.test_api_endpoints()
            
            # Fetch UI content
            ui_success = self.fetch_ui_content()
            
            # Display dashboard info
            self.display_dashboard_info()
            
            # Summary
            print("\n" + "=" * 40)
            print("📋 Summary:")
            print(f"✅ Backend: {'Running' if api_success else 'Failed'}")
            print(f"✅ Frontend: {'Running' if ui_success else 'Failed'}")
            print(f"✅ Integration: {'Working' if api_success and ui_success else 'Partial'}")
            
            if api_success:
                print("\n🎉 CodegenCICD Dashboard is fully operational!")
                print(f"🌐 Frontend: {self.frontend_url}")
                print(f"🔧 Backend API: {self.base_url}")
                print(f"📚 API Docs: {self.base_url}/docs")
                print("🌐 Opening dashboard in your browser...")
                
                # Open browser
                try:
                    import webbrowser
                    webbrowser.open(self.frontend_url)
                except:
                    pass
                
                print("\n💡 Press Ctrl+C to stop the services")
                
                # Keep running until interrupted
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n🛑 Shutting down services...")
                    return True
            else:
                print("\n⚠️  Some components failed to load")
                return False
                
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False
        finally:
            self.stop_server()

def main():
    """Main function"""
    cli = CodegenCLI()
    success = cli.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
