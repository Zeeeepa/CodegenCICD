#!/usr/bin/env python3
"""
Web-Eval Command Simulator
Simulates: web-eval --url https://uioftheproject.com --instruction cicd_cycle_instructions.txt
"""

import os
import sys
import json
import argparse
from pathlib import Path
from simple_web_eval_test import SimpleWebEvaluator

class WebEvalCommandSimulator:
    def __init__(self):
        self.config_file = "web_eval_environment_config.json"
        self.load_configuration()
        
    def load_configuration(self):
        """Load environment configuration"""
        if Path(self.config_file).exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}
    
    def validate_environment(self) -> dict:
        """Validate required environment variables"""
        print("🔍 Validating environment variables...")
        
        validation_results = {
            "basic_functionality": {"required": [], "missing": [], "present": []},
            "web_eval": {"required": [], "missing": [], "present": []},
            "production": {"required": [], "missing": [], "present": []}
        }
        
        # Get validation rules from config
        validation_rules = self.config.get("ui_configuration", {}).get("validation_rules", {})
        
        # Check basic functionality variables
        basic_required = validation_rules.get("required_for_basic_functionality", [])
        for var in basic_required:
            validation_results["basic_functionality"]["required"].append(var)
            if os.getenv(var):
                validation_results["basic_functionality"]["present"].append(var)
                print(f"✅ {var}: Present")
            else:
                validation_results["basic_functionality"]["missing"].append(var)
                print(f"❌ {var}: Missing")
        
        # Check web-eval variables
        web_eval_required = validation_rules.get("required_for_web_eval", [])
        for var in web_eval_required:
            validation_results["web_eval"]["required"].append(var)
            if os.getenv(var):
                validation_results["web_eval"]["present"].append(var)
                print(f"✅ {var}: Present")
            else:
                validation_results["web_eval"]["missing"].append(var)
                print(f"❌ {var}: Missing")
        
        # Check production recommended variables
        prod_recommended = validation_rules.get("recommended_for_production", [])
        for var in prod_recommended:
            validation_results["production"]["required"].append(var)
            if os.getenv(var):
                validation_results["production"]["present"].append(var)
                print(f"✅ {var}: Present")
            else:
                validation_results["production"]["missing"].append(var)
                print(f"⚠️  {var}: Missing (recommended)")
        
        return validation_results
    
    def generate_environment_setup_guide(self, validation_results: dict) -> str:
        """Generate setup guide for missing variables"""
        guide = []
        guide.append("🔧 ENVIRONMENT SETUP GUIDE")
        guide.append("=" * 50)
        
        # Basic functionality
        basic_missing = validation_results["basic_functionality"]["missing"]
        if basic_missing:
            guide.append("\\n❌ CRITICAL: Missing basic functionality variables:")
            for var in basic_missing:
                var_config = self.get_variable_config(var)
                if var_config:
                    guide.append(f"  {var}={var_config.get('example', 'your_value_here')}")
                    guide.append(f"    Description: {var_config.get('description', 'No description')}")
                else:
                    guide.append(f"  {var}=your_value_here")
        
        # Web-eval variables
        web_eval_missing = validation_results["web_eval"]["missing"]
        if web_eval_missing:
            guide.append("\\n⚠️  Missing web-eval-agent variables:")
            for var in web_eval_missing:
                var_config = self.get_variable_config(var)
                if var_config:
                    guide.append(f"  {var}={var_config.get('example', 'your_value_here')}")
                    guide.append(f"    Description: {var_config.get('description', 'No description')}")
                else:
                    guide.append(f"  {var}=your_value_here")
        
        # Production variables
        prod_missing = validation_results["production"]["missing"]
        if prod_missing:
            guide.append("\\n💡 Recommended production variables:")
            for var in prod_missing:
                var_config = self.get_variable_config(var)
                if var_config:
                    guide.append(f"  {var}={var_config.get('example', var_config.get('default', 'your_value_here'))}")
                    guide.append(f"    Description: {var_config.get('description', 'No description')}")
                else:
                    guide.append(f"  {var}=your_value_here")
        
        guide.append("\\n📝 Add these to your .env file or set them in the UI settings dialog.")
        
        return "\\n".join(guide)
    
    def get_variable_config(self, var_name: str) -> dict:
        """Get configuration for a specific variable"""
        categories = self.config.get("web_eval_agent_environment_variables", {}).get("categories", {})
        
        for category_name, category_data in categories.items():
            variables = category_data.get("variables", {})
            if var_name in variables:
                return variables[var_name]
        
        return {}
    
    def run_web_eval_test(self, url: str, instruction_file: str) -> dict:
        """Run the web evaluation test"""
        print(f"🚀 Running web-eval simulation...")
        print(f"🎯 Target URL: {url}")
        print(f"📋 Instructions: {instruction_file}")
        
        # Check if instruction file exists
        if not Path(instruction_file).exists():
            print(f"⚠️  Instruction file not found: {instruction_file}")
            print("   Using built-in test instructions...")
        
        # Run the evaluation
        evaluator = SimpleWebEvaluator(url)
        results = evaluator.run_comprehensive_test()
        
        # Add web-eval specific metadata
        results["web_eval_metadata"] = {
            "command_simulated": f"web-eval --url {url} --instruction {instruction_file}",
            "environment_validated": True,
            "instruction_file": instruction_file,
            "simulator_version": "1.0.0"
        }
        
        return results
    
    def generate_web_eval_report(self, results: dict, validation_results: dict) -> str:
        """Generate comprehensive web-eval report"""
        report = []
        report.append("🧪 WEB-EVAL-AGENT CICD CYCLE REPORT")
        report.append("=" * 60)
        report.append(f"Command: {results.get('web_eval_metadata', {}).get('command_simulated', 'N/A')}")
        report.append(f"Target URL: {results.get('target_url', 'N/A')}")
        report.append(f"Overall Score: {results.get('overall_score', 0):.1f}%")
        report.append(f"Test Status: {results.get('status', 'unknown')}")
        report.append(f"Duration: {results.get('duration_seconds', 0):.2f} seconds")
        
        # Environment validation summary
        report.append("\\n🔧 ENVIRONMENT VALIDATION:")
        basic_missing = len(validation_results["basic_functionality"]["missing"])
        web_eval_missing = len(validation_results["web_eval"]["missing"])
        
        if basic_missing == 0 and web_eval_missing == 0:
            report.append("  ✅ All required variables present")
        elif basic_missing > 0:
            report.append(f"  ❌ {basic_missing} critical variables missing")
        elif web_eval_missing > 0:
            report.append(f"  ⚠️  {web_eval_missing} web-eval variables missing")
        
        # Test results summary
        report.append("\\n📊 TEST RESULTS:")
        scores = results.get("scores", {})
        report.append(f"  UI Components: {scores.get('ui_score', 0):.1f}%")
        report.append(f"  API Endpoints: {scores.get('api_score', 0):.1f}%")
        report.append(f"  Static Assets: {scores.get('asset_score', 0):.1f}%")
        
        # Recommendations
        report.append("\\n💡 RECOMMENDATIONS:")
        recommendations = results.get("recommendations", [])
        for rec in recommendations:
            report.append(f"  {rec}")
        
        # Environment setup if needed
        if basic_missing > 0 or web_eval_missing > 0:
            report.append("\\n" + self.generate_environment_setup_guide(validation_results))
        
        return "\\n".join(report)
    
    def run(self, url: str, instruction_file: str) -> bool:
        """Run the complete web-eval simulation"""
        print("🚀 WEB-EVAL-AGENT COMMAND SIMULATOR")
        print("=" * 60)
        
        # Validate environment
        validation_results = self.validate_environment()
        
        # Check if basic functionality is available
        basic_missing = validation_results["basic_functionality"]["missing"]
        if basic_missing:
            print("\\n❌ CRITICAL: Missing required environment variables!")
            print(self.generate_environment_setup_guide(validation_results))
            return False
        
        # Run web evaluation test
        test_results = self.run_web_eval_test(url, instruction_file)
        
        # Generate and display report
        report = self.generate_web_eval_report(test_results, validation_results)
        print("\\n" + report)
        
        # Save results
        results_file = "web_eval_command_results.json"
        combined_results = {
            "test_results": test_results,
            "validation_results": validation_results,
            "timestamp": test_results.get("timestamp"),
            "command_simulated": f"web-eval --url {url} --instruction {instruction_file}"
        }
        
        with open(results_file, 'w') as f:
            json.dump(combined_results, f, indent=2)
        
        print(f"\\n💾 Results saved to: {results_file}")
        
        # Return success based on overall score
        overall_score = test_results.get("overall_score", 0)
        return overall_score >= 70

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Web-Eval Command Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python web_eval_command_simulator.py --url http://localhost:3001 --instruction cicd_cycle_instructions.txt
  python web_eval_command_simulator.py --url https://uioftheproject.com --instruction cicd_cycle_instructions.txt
  
This simulates: web-eval --url <URL> --instruction <FILE>
        """
    )
    
    parser.add_argument("--url", required=True, help="Target URL to test")
    parser.add_argument("--instruction", required=True, help="Instruction file for the test")
    
    args = parser.parse_args()
    
    # Run the simulation
    simulator = WebEvalCommandSimulator()
    success = simulator.run(args.url, args.instruction)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

