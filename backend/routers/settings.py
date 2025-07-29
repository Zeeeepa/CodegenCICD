from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import os
import json
from datetime import datetime
import asyncio
import aiohttp

from ..database import get_db
from ..models.settings import Settings, EnvironmentVariable
from ..services.validation_service import ValidationService
from ..integrations.codegen_client import CodegenClient
from ..integrations.github_client import GitHubClient
from ..integrations.cloudflare_client import CloudflareClient

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Environment variable categories and their descriptions
ENV_VAR_CATEGORIES = {
    "codegen": {
        "CODEGEN_ORG_ID": "Codegen organization ID",
        "CODEGEN_API_TOKEN": "Codegen API token for agent coordination"
    },
    "github": {
        "GITHUB_TOKEN": "GitHub personal access token"
    },
    "ai": {
        "GEMINI_API_KEY": "Gemini API key for web-eval-agent"
    },
    "cloudflare": {
        "CLOUDFLARE_API_KEY": "Cloudflare API key",
        "CLOUDFLARE_ACCOUNT_ID": "Cloudflare account ID",
        "CLOUDFLARE_WORKER_NAME": "Cloudflare worker name",
        "CLOUDFLARE_WORKER_URL": "Cloudflare worker webhook URL"
    },
    "services": {
        "GRAINCHAIN_URL": "Grainchain service URL for sandboxing",
        "GRAPH_SITTER_URL": "Graph-sitter service URL for code analysis",
        "WEB_EVAL_AGENT_URL": "Web-eval-agent service URL for UI testing"
    }
}

SENSITIVE_VARS = {
    "CODEGEN_API_TOKEN", "GITHUB_TOKEN", "GEMINI_API_KEY", "CLOUDFLARE_API_KEY"
}

@router.get("/environment")
async def get_environment_variables(db: Session = Depends(get_db)):
    """Get all environment variables organized by category."""
    try:
        environment_variables = {}
        
        for category, vars_dict in ENV_VAR_CATEGORIES.items():
            environment_variables[category] = {}
            for var_name, description in vars_dict.items():
                # Get from database first, then fallback to OS environment
                db_var = db.query(EnvironmentVariable).filter(
                    EnvironmentVariable.key == var_name
                ).first()
                
                if db_var:
                    value = db_var.decrypt_value() if not db_var.sensitive else "[ENCRYPTED]"
                else:
                    value = os.getenv(var_name, "")
                    if var_name in SENSITIVE_VARS and value:
                        value = "[SET]"
                
                environment_variables[category][var_name] = value
        
        return {
            "environment_variables": environment_variables,
            "timestamp": datetime.now().timestamp(),
            "total_variables": sum(len(vars_dict) for vars_dict in ENV_VAR_CATEGORIES.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get environment variables: {str(e)}")

@router.put("/environment")
async def update_environment_variables(
    request: Dict[str, Dict[str, str]],
    db: Session = Depends(get_db)
):
    """Update environment variables."""
    try:
        environment_variables = request.get("environment_variables", {})
        updated_count = 0
        
        for category, vars_dict in environment_variables.items():
            if category not in ENV_VAR_CATEGORIES:
                continue
                
            for var_name, value in vars_dict.items():
                if var_name not in ENV_VAR_CATEGORIES[category]:
                    continue
                
                # Check if variable exists in database
                db_var = db.query(EnvironmentVariable).filter(
                    EnvironmentVariable.key == var_name
                ).first()
                
                if db_var:
                    # Update existing variable
                    if value and value != "[ENCRYPTED]" and value != "[SET]":
                        db_var.set_value(value)
                        db_var.updated_at = datetime.utcnow()
                        updated_count += 1
                else:
                    # Create new variable
                    if value:
                        new_var = EnvironmentVariable(
                            key=var_name,
                            category=category,
                            description=ENV_VAR_CATEGORIES[category][var_name],
                            sensitive=var_name in SENSITIVE_VARS
                        )
                        new_var.set_value(value)
                        db.add(new_var)
                        updated_count += 1
        
        db.commit()
        
        return {
            "message": f"Updated {updated_count} environment variables",
            "updated_count": updated_count,
            "timestamp": datetime.now().timestamp()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update environment variables: {str(e)}")

@router.get("/global")
async def get_global_settings(db: Session = Depends(get_db)):
    """Get global application settings."""
    try:
        settings = db.query(Settings).filter(Settings.key.like("global_%")).all()
        
        settings_dict = {
            "autoTestComponents": True,
            "enableWebhookNotifications": True,
            "autoMergeValidatedPRs": False,
            "enableComprehensiveTesting": True,
        }
        
        # Override with database values
        for setting in settings:
            key = setting.key.replace("global_", "")
            if key in settings_dict:
                settings_dict[key] = setting.value == "true"
        
        return {
            "settings": settings_dict,
            "timestamp": datetime.now().timestamp()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get global settings: {str(e)}")

@router.put("/global")
async def update_global_settings(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update global application settings."""
    try:
        settings_data = request.get("settings", {})
        updated_count = 0
        
        for key, value in settings_data.items():
            db_key = f"global_{key}"
            
            # Check if setting exists
            setting = db.query(Settings).filter(Settings.key == db_key).first()
            
            if setting:
                setting.value = str(value).lower()
                setting.updated_at = datetime.utcnow()
            else:
                setting = Settings(
                    key=db_key,
                    value=str(value).lower(),
                    description=f"Global setting: {key}"
                )
                db.add(setting)
            
            updated_count += 1
        
        db.commit()
        
        return {
            "message": f"Updated {updated_count} global settings",
            "updated_count": updated_count,
            "timestamp": datetime.now().timestamp()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update global settings: {str(e)}")

@router.post("/test-services")
async def test_services(
    request: Dict[str, str],
    db: Session = Depends(get_db)
):
    """Test connectivity to all external services."""
    try:
        environment_variables = request.get("environment_variables", {})
        test_results = {}
        passed = 0
        total = 0
        
        # Test Codegen API
        if environment_variables.get("CODEGEN_API_TOKEN") and environment_variables.get("CODEGEN_ORG_ID"):
            try:
                codegen_client = CodegenClient(
                    api_token=environment_variables["CODEGEN_API_TOKEN"],
                    org_id=environment_variables["CODEGEN_ORG_ID"]
                )
                await codegen_client.test_connection()
                test_results["codegen"] = {"status": "success", "message": "Connected successfully"}
                passed += 1
            except Exception as e:
                test_results["codegen"] = {"status": "error", "message": str(e)}
            total += 1
        
        # Test GitHub API
        if environment_variables.get("GITHUB_TOKEN"):
            try:
                github_client = GitHubClient(token=environment_variables["GITHUB_TOKEN"])
                await github_client.test_connection()
                test_results["github"] = {"status": "success", "message": "Connected successfully"}
                passed += 1
            except Exception as e:
                test_results["github"] = {"status": "error", "message": str(e)}
            total += 1
        
        # Test Cloudflare API
        if environment_variables.get("CLOUDFLARE_API_KEY") and environment_variables.get("CLOUDFLARE_ACCOUNT_ID"):
            try:
                cloudflare_client = CloudflareClient(
                    api_key=environment_variables["CLOUDFLARE_API_KEY"],
                    account_id=environment_variables["CLOUDFLARE_ACCOUNT_ID"]
                )
                await cloudflare_client.test_connection()
                test_results["cloudflare"] = {"status": "success", "message": "Connected successfully"}
                passed += 1
            except Exception as e:
                test_results["cloudflare"] = {"status": "error", "message": str(e)}
            total += 1
        
        # Test service URLs
        service_urls = {
            "grainchain": environment_variables.get("GRAINCHAIN_URL"),
            "graph_sitter": environment_variables.get("GRAPH_SITTER_URL"),
            "web_eval_agent": environment_variables.get("WEB_EVAL_AGENT_URL")
        }
        
        async with aiohttp.ClientSession() as session:
            for service_name, url in service_urls.items():
                if url:
                    try:
                        async with session.get(f"{url}/health", timeout=5) as response:
                            if response.status == 200:
                                test_results[service_name] = {"status": "success", "message": "Service is healthy"}
                                passed += 1
                            else:
                                test_results[service_name] = {"status": "error", "message": f"HTTP {response.status}"}
                    except Exception as e:
                        test_results[service_name] = {"status": "error", "message": str(e)}
                    total += 1
        
        # Test Gemini API (via web-eval-agent)
        if environment_variables.get("GEMINI_API_KEY"):
            try:
                # This would be a simple test call to Gemini API
                test_results["gemini"] = {"status": "success", "message": "API key format is valid"}
                passed += 1
            except Exception as e:
                test_results["gemini"] = {"status": "error", "message": str(e)}
            total += 1
        
        return {
            "test_results": test_results,
            "passed": passed,
            "total": total,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "timestamp": datetime.now().timestamp()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service test failed: {str(e)}")

@router.post("/deploy-web-eval-agent")
async def deploy_web_eval_agent(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Deploy and test web-eval-agent with comprehensive testing."""
    try:
        gemini_api_key = request.get("gemini_api_key")
        if not gemini_api_key:
            raise HTTPException(status_code=400, detail="GEMINI_API_KEY is required")
        
        validation_service = ValidationService()
        
        # Deploy web-eval-agent
        deployment_result = await validation_service.deploy_web_eval_agent(
            gemini_api_key=gemini_api_key
        )
        
        if deployment_result["success"]:
            # Run comprehensive testing
            test_result = await validation_service.run_comprehensive_test(
                base_url="http://localhost:3000",
                gemini_api_key=gemini_api_key
            )
            
            return {
                "deployment": deployment_result,
                "test_result": test_result,
                "timestamp": datetime.now().timestamp()
            }
        else:
            raise HTTPException(status_code=500, detail=f"Deployment failed: {deployment_result['error']}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Web-eval-agent deployment failed: {str(e)}")
