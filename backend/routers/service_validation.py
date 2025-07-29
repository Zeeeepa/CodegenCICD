"""
Service validation endpoints for checking API connectivity and functionality
"""
import os
import time
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
import httpx
import requests
from github import Github
import google.generativeai as genai

router = APIRouter(prefix="/api/validation", tags=["service_validation"])

class ServiceValidator:
    """Service validation utility class"""
    
    @staticmethod
    async def validate_codegen_api() -> Dict[str, Any]:
        """Validate Codegen API connectivity and authentication"""
        start_time = time.time()
        
        try:
            org_id = os.getenv("CODEGEN_ORG_ID")
            api_token = os.getenv("CODEGEN_API_TOKEN")
            
            if not org_id or not api_token:
                return {
                    "status": "error",
                    "message": "Missing CODEGEN_ORG_ID or CODEGEN_API_TOKEN environment variables",
                    "response_time": 0,
                    "details": {
                        "org_id_present": bool(org_id),
                        "api_token_present": bool(api_token),
                        "api_token_format": api_token.startswith("sk-") if api_token else False
                    }
                }
            
            # Test API connectivity
            headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test with agent runs endpoint instead of organizations
                response = await client.get(
                    f"https://api.codegen.com/v1/agent-runs",
                    headers=headers,
                    params={"limit": 1}
                )
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "success",
                        "message": "Codegen API connection successful",
                        "response_time": round(response_time * 1000, 2),
                        "details": {
                            "org_id": org_id,
                            "endpoint_tested": "agent-runs",
                            "api_version": "v1",
                            "authenticated": True,
                            "response_count": len(data.get("data", []))
                        }
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Codegen API returned status {response.status_code}",
                        "response_time": round(response_time * 1000, 2),
                        "details": {
                            "status_code": response.status_code,
                            "response_text": response.text[:200]
                        }
                    }
                    
        except httpx.TimeoutException:
            return {
                "status": "error",
                "message": "Codegen API request timed out",
                "response_time": round((time.time() - start_time) * 1000, 2),
                "details": {"timeout": True}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Codegen API validation failed: {str(e)}",
                "response_time": round((time.time() - start_time) * 1000, 2),
                "details": {"error": str(e)}
            }
    
    @staticmethod
    async def validate_github_api() -> Dict[str, Any]:
        """Validate GitHub API connectivity and authentication"""
        start_time = time.time()
        
        try:
            github_token = os.getenv("GITHUB_TOKEN")
            
            if not github_token:
                return {
                    "status": "error",
                    "message": "Missing GITHUB_TOKEN environment variable",
                    "response_time": 0,
                    "details": {
                        "token_present": False,
                        "token_format": False
                    }
                }
            
            # Validate token format
            valid_prefixes = ["ghp_", "github_pat_", "gho_", "ghu_", "ghs_", "ghr_"]
            token_format_valid = any(github_token.startswith(prefix) for prefix in valid_prefixes)
            
            # Test GitHub API
            github = Github(github_token)
            user = github.get_user()
            
            response_time = time.time() - start_time
            
            return {
                "status": "success",
                "message": "GitHub API connection successful",
                "response_time": round(response_time * 1000, 2),
                "details": {
                    "username": user.login,
                    "user_id": user.id,
                    "token_format_valid": token_format_valid,
                    "rate_limit": github.get_rate_limit().core.remaining,
                    "authenticated": True
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"GitHub API validation failed: {str(e)}",
                "response_time": round((time.time() - start_time) * 1000, 2),
                "details": {
                    "error": str(e),
                    "token_format_valid": token_format_valid if 'token_format_valid' in locals() else False
                }
            }
    
    @staticmethod
    async def validate_gemini_api() -> Dict[str, Any]:
        """Validate Gemini API connectivity and authentication"""
        start_time = time.time()
        
        try:
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            
            if not gemini_api_key:
                return {
                    "status": "error",
                    "message": "Missing GEMINI_API_KEY environment variable",
                    "response_time": 0,
                    "details": {
                        "api_key_present": False,
                        "api_key_format": False
                    }
                }
            
            # Validate API key format
            api_key_format_valid = gemini_api_key.startswith("AIza")
            
            # Configure Gemini
            genai.configure(api_key=gemini_api_key)
            
            # Test with a simple request using the current model name
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content("Hello, this is a test. Please respond with 'API working'.")
            
            response_time = time.time() - start_time
            
            return {
                "status": "success",
                "message": "Gemini API connection successful",
                "response_time": round(response_time * 1000, 2),
                "details": {
                    "api_key_format_valid": api_key_format_valid,
                    "model": "gemini-1.5-flash",
                    "test_response": response.text[:100] if response.text else "No response",
                    "authenticated": True
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Gemini API validation failed: {str(e)}",
                "response_time": round((time.time() - start_time) * 1000, 2),
                "details": {
                    "error": str(e),
                    "api_key_format_valid": api_key_format_valid if 'api_key_format_valid' in locals() else False
                }
            }
    
    @staticmethod
    async def validate_cloudflare_api() -> Dict[str, Any]:
        """Validate Cloudflare API connectivity and authentication"""
        start_time = time.time()
        
        try:
            api_key = os.getenv("CLOUDFLARE_API_KEY")
            account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
            email = os.getenv("CLOUDFLARE_EMAIL", "admin@example.com")
            worker_url = os.getenv("CLOUDFLARE_WORKER_URL")
            
            if not api_key or not account_id:
                return {
                    "status": "error",
                    "message": "Missing CLOUDFLARE_API_KEY or CLOUDFLARE_ACCOUNT_ID environment variables",
                    "response_time": 0,
                    "details": {
                        "api_key_present": bool(api_key),
                        "account_id_present": bool(account_id),
                        "worker_url_present": bool(worker_url)
                    }
                }
            
            # Test Cloudflare API
            headers = {
                "X-Auth-Key": api_key,
                "X-Auth-Email": email,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test account access
                response = await client.get(
                    f"https://api.cloudflare.com/client/v4/accounts/{account_id}",
                    headers=headers
                )
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    account_info = data.get("result", {})
                    
                    # Test worker URL if provided
                    worker_status = "not_configured"
                    if worker_url:
                        try:
                            worker_response = await client.get(worker_url, timeout=5.0)
                            worker_status = "accessible" if worker_response.status_code < 500 else "error"
                        except:
                            worker_status = "unreachable"
                    
                    return {
                        "status": "success",
                        "message": "Cloudflare API connection successful",
                        "response_time": round(response_time * 1000, 2),
                        "details": {
                            "account_id": account_id,
                            "account_name": account_info.get("name", "Unknown"),
                            "worker_url": worker_url,
                            "worker_status": worker_status,
                            "authenticated": True
                        }
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Cloudflare API returned status {response.status_code}",
                        "response_time": round(response_time * 1000, 2),
                        "details": {
                            "status_code": response.status_code,
                            "response_text": response.text[:200]
                        }
                    }
                    
        except httpx.TimeoutException:
            return {
                "status": "error",
                "message": "Cloudflare API request timed out",
                "response_time": round((time.time() - start_time) * 1000, 2),
                "details": {"timeout": True}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Cloudflare API validation failed: {str(e)}",
                "response_time": round((time.time() - start_time) * 1000, 2),
                "details": {"error": str(e)}
            }

# API Endpoints
@router.get("/services")
async def validate_all_services():
    """Validate all configured services"""
    validator = ServiceValidator()
    
    # Run all validations concurrently
    results = await asyncio.gather(
        validator.validate_codegen_api(),
        validator.validate_github_api(),
        validator.validate_gemini_api(),
        validator.validate_cloudflare_api(),
        return_exceptions=True
    )
    
    services = ["codegen", "github", "gemini", "cloudflare"]
    validation_results = {}
    
    for i, result in enumerate(results):
        service_name = services[i]
        if isinstance(result, Exception):
            validation_results[service_name] = {
                "status": "error",
                "message": f"Validation failed with exception: {str(result)}",
                "response_time": 0,
                "details": {"exception": str(result)}
            }
        else:
            validation_results[service_name] = result
    
    # Calculate overall status
    all_successful = all(result.get("status") == "success" for result in validation_results.values())
    
    return {
        "overall_status": "success" if all_successful else "partial_failure",
        "services": validation_results,
        "timestamp": time.time(),
        "summary": {
            "total_services": len(services),
            "successful": sum(1 for result in validation_results.values() if result.get("status") == "success"),
            "failed": sum(1 for result in validation_results.values() if result.get("status") == "error")
        }
    }

@router.get("/services/{service_name}")
async def validate_single_service(service_name: str):
    """Validate a single service"""
    validator = ServiceValidator()
    
    validation_methods = {
        "codegen": validator.validate_codegen_api,
        "github": validator.validate_github_api,
        "gemini": validator.validate_gemini_api,
        "cloudflare": validator.validate_cloudflare_api
    }
    
    if service_name not in validation_methods:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown service: {service_name}. Available services: {list(validation_methods.keys())}"
        )
    
    result = await validation_methods[service_name]()
    result["timestamp"] = time.time()
    
    return result

@router.get("/environment")
async def get_environment_variables():
    """Get all environment variables (visible, not masked)"""
    env_vars = {
        "codegen": {
            "CODEGEN_ORG_ID": os.getenv("CODEGEN_ORG_ID", ""),
            "CODEGEN_API_TOKEN": os.getenv("CODEGEN_API_TOKEN", "")
        },
        "github": {
            "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", "")
        },
        "gemini": {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", "")
        },
        "cloudflare": {
            "CLOUDFLARE_API_KEY": os.getenv("CLOUDFLARE_API_KEY", ""),
            "CLOUDFLARE_ACCOUNT_ID": os.getenv("CLOUDFLARE_ACCOUNT_ID", ""),
            "CLOUDFLARE_WORKER_NAME": os.getenv("CLOUDFLARE_WORKER_NAME", ""),
            "CLOUDFLARE_WORKER_URL": os.getenv("CLOUDFLARE_WORKER_URL", "")
        },
        "service_config": {
            "BACKEND_PORT": os.getenv("BACKEND_PORT", "8000"),
            "FRONTEND_PORT": os.getenv("FRONTEND_PORT", "3001"),
            "BACKEND_HOST": os.getenv("BACKEND_HOST", "localhost"),
            "FRONTEND_HOST": os.getenv("FRONTEND_HOST", "localhost")
        }
    }
    
    return {
        "environment_variables": env_vars,
        "timestamp": time.time(),
        "total_variables": sum(len(category) for category in env_vars.values())
    }

@router.put("/environment/{variable_name}")
async def update_environment_variable(variable_name: str, value: dict):
    """Update an environment variable"""
    try:
        new_value = value.get("value", "")
        
        # Set the environment variable
        os.environ[variable_name] = new_value
        
        # In a production environment, you might want to persist this to a .env file
        # For now, we'll just update the runtime environment
        
        return {
            "success": True,
            "message": f"Environment variable {variable_name} updated successfully",
            "variable": variable_name,
            "value": new_value,
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update environment variable: {str(e)}"
        )

@router.get("/github-repositories")
async def get_github_repositories():
    """Get GitHub repositories from the user's account"""
    try:
        github_token = os.getenv("GITHUB_TOKEN")
        
        if not github_token:
            raise HTTPException(
                status_code=400,
                detail="GitHub token not configured"
            )
        
        github = Github(github_token)
        user = github.get_user()
        
        # Get user's repositories
        repos = []
        for repo in user.get_repos():
            repos.append({
                "id": repo.id,
                "name": repo.name,
                "full_name": repo.full_name,
                "private": repo.private,
                "url": repo.html_url,
                "owner": repo.owner.login,
                "description": repo.description,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                "language": repo.language,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count
            })
        
        return {
            "repositories": repos,
            "total_count": len(repos),
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch GitHub repositories: {str(e)}"
        )
