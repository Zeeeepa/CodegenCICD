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
        
    def start_server(self):
        """Start the CodegenCICD server"""
        print("🚀 Starting CodegenCICD Dashboard...")
        
        # Set environment variables
        env = os.environ.copy()
        env["DATABASE_URL"] = "sqlite+aiosqlite:///./codegencd.db"
        
        # Start the server
        self.server_process = subprocess.Popen(
            ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd="backend",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        print("⏳ Waiting for server to start...")
        for i in range(10):
            try:
                response = requests.get(f"{self.base_url}/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Server started successfully!")
                    return True
            except:
                time.sleep(1)
                continue
        
        print("❌ Failed to start server")
        return False
    
    def stop_server(self):
        """Stop the server"""
        if self.server_process:
            print("🛑 Stopping server...")
            self.server_process.terminate()
            self.server_process.wait()
            print("✅ Server stopped")
    
    def fetch_ui_content(self):
        """Fetch and display UI content"""
        try:
            print("📱 Fetching UI content...")
            
            # Get the main dashboard page
            response = requests.get(f"{self.base_url}/dashboard", timeout=10)
            if response.status_code == 200:
                print("✅ Dashboard UI loaded successfully!")
                print(f"📄 Content length: {len(response.text)} characters")
                
                # Extract key information from the HTML
                html_content = response.text
                if "CodegenCICD Dashboard" in html_content:
                    print("✅ Dashboard title found")
                if "Material+Icons" in html_content:
                    print("✅ Material-UI icons loaded")
                if "main.033a881b.js" in html_content:
                    print("✅ React JavaScript bundle loaded")
                if "main.44758348.css" in html_content:
                    print("✅ CSS styles loaded")
                
                return True
            else:
                print(f"❌ Failed to load dashboard: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error fetching UI content: {e}")
            return False
    
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
            
            print(f"🌐 Dashboard URL: {self.base_url}/dashboard")
            
        except Exception as e:
            print(f"❌ Error getting dashboard info: {e}")
    
    def run(self):
        """Main CLI execution"""
        print("🎯 CodegenCICD Dashboard CLI")
        print("=" * 40)
        
        try:
            # Start server
            if not self.start_server():
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
            print(f"✅ Server: {'Running' if api_success else 'Failed'}")
            print(f"✅ API: {'Working' if api_success else 'Failed'}")
            print(f"✅ UI: {'Loaded' if ui_success else 'Failed'}")
            
            if api_success and ui_success:
                print("\n🎉 CodegenCICD Dashboard is fully operational!")
                print(f"🌐 Access at: {self.base_url}/dashboard")
                return True
            else:
                print("\n⚠️  Some components failed to load")
                return False
                
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
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
