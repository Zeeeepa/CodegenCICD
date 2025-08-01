#!/usr/bin/env python3
"""
CodegenCICD CLI - Command line interface for the CodegenCICD Dashboard
Main entry point for the 'codegen' command
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
from typing import Dict, List, Optional

class CodegenCLI:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3001"
        self.server_process = None
        self.frontend_process = None
        self.required_env_vars = {
            "CODEGEN_ORG_ID": "Your Codegen organization ID",
            "CODEGEN_API_TOKEN": "Your Codegen API token (starts with sk-)",
            "GITHUB_TOKEN": "Your GitHub personal access token"
        }
        self.optional_env_vars = {
            "GEMINI_API_KEY": "Google Gemini API key for web evaluation",
            "CLOUDFLARE_API_KEY": "Cloudflare API key for webhook gateway",
            "CLOUDFLARE_ACCOUNT_ID": "Cloudflare account ID",
            "CLOUDFLARE_WORKER_NAME": "Cloudflare worker name (default: webhook-gateway)",
            "CLOUDFLARE_WORKER_URL": "Cloudflare worker URL"
        }
    
    def check_environment(self) -> bool:
        """Check if required environment variables are set"""
        missing_required = []
        missing_optional = []
        
        # Load .env file if it exists
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
        
        # Check required variables
        for var, description in self.required_env_vars.items():
            if not os.getenv(var):
                missing_required.append((var, description))
        
        # Check optional variables
        for var, description in self.optional_env_vars.items():
            if not os.getenv(var):
                missing_optional.append((var, description))
        
        if missing_required:
            print("⚠️  Missing required environment variables. Please add to .env file:")
            print()
            print("# Required for core functionality")
            for var, desc in missing_required:
                print(f"{var}=your-{var.lower().replace('_', '-')}")
            
            if missing_optional:
                print()
                print("# Optional for advanced features")
                for var, desc in missing_optional:
                    print(f"{var}=your-{var.lower().replace('_', '-')}")
            
            print()
            print("Create .env file with these variables and run 'codegen' again.")
            print("For help getting API keys, see: https://github.com/Zeeeepa/CodegenCICD#setup")
            return False
        
        return True
    
    def start_services(self):
        """Start both backend and frontend services"""
        print("🚀 Starting CodegenCICD Dashboard...")
        
        # Use the start.sh script which handles everything
        try:
            # Make start.sh executable
            os.chmod("start.sh", 0o755)
            
            # Start services using the start script
            print("⏳ Starting backend and frontend services...")
            
            # Run start.sh in the background
            self.server_process = subprocess.Popen(
                ["./start.sh"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for services to start
            print("⏳ Waiting for services to start...")
            for i in range(60):  # Wait up to 60 seconds
                try:
                    # Check backend
                    backend_response = requests.get(f"{self.base_url}/health", timeout=2)
                    # Check frontend
                    frontend_response = requests.get(self.frontend_url, timeout=2)
                    
                    if backend_response.status_code == 200 and frontend_response.status_code == 200:
                        print("✅ Backend and frontend started successfully!")
                        return True
                except:
                    time.sleep(1)
                    continue
            
            print("❌ Failed to start services within 60 seconds")
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
        """Fetch and display UI content"""
        try:
            print("📱 Fetching UI content...")
            
            # Get the main frontend page
            response = requests.get(self.frontend_url, timeout=10)
            if response.status_code == 200:
                print("✅ Frontend UI loaded successfully!")
                print(f"📄 Content length: {len(response.text)} characters")
                
                # Extract key information from the HTML
                html_content = response.text
                if "CodegenCICD Dashboard" in html_content:
                    print("✅ Dashboard title found")
                if "react" in html_content.lower():
                    print("✅ React application detected")
                if "static/js" in html_content:
                    print("✅ JavaScript bundles loaded")
                if "static/css" in html_content:
                    print("✅ CSS styles loaded")
                
                return True
            else:
                print(f"❌ Failed to load frontend: {response.status_code}")
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
            
            print(f"🌐 Frontend URL: {self.frontend_url}")
            print(f"🔧 Backend URL: {self.base_url}")
            
        except Exception as e:
            print(f"❌ Error getting dashboard info: {e}")
    
    def run(self):
        """Main CLI execution"""
        print("🎯 CodegenCICD Dashboard")
        print("=" * 40)
        
        try:
            # Check environment variables first
            if not self.check_environment():
                return False
            
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
            print(f"✅ Integration: {'Working' if api_success and ui_success else 'Failed'}")
            
            if api_success and ui_success:
                print("\n🎉 CodegenCICD Dashboard is fully operational!")
                print(f"🌐 Frontend: {self.frontend_url}")
                print(f"🔧 Backend API: {self.base_url}")
                print(f"📚 API Docs: {self.base_url}/docs")
                
                # Try to open browser
                try:
                    webbrowser.open(self.frontend_url)
                    print("🌐 Opening dashboard in your browser...")
                except:
                    print("💡 Open the dashboard manually in your browser")
                
                print("\n💡 Press Ctrl+C to stop the services")
                
                # Keep running until interrupted
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n🛑 Stopping services...")
                
                return True
            else:
                print("\n⚠️  Some components failed to load")
                return False
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping services...")
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
