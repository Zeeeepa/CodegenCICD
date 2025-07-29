from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import os
from datetime import datetime

from backend.database import get_db
from backend.models.project import Project
from backend.models.settings import EnvironmentVariable
from backend.integrations.github_client import GitHubClient
from backend.integrations.cloudflare_client import CloudflareClient, generate_webhook_worker_script

router = APIRouter(prefix="/api/github", tags=["github"])

def get_github_client(db: Session = Depends(get_db)) -> GitHubClient:
    """Get GitHub client with token from environment variables."""
    # Try to get token from database first
    github_token_var = db.query(EnvironmentVariable).filter(
        EnvironmentVariable.key == "GITHUB_TOKEN"
    ).first()
    
    if github_token_var:
        token = github_token_var.get_value()
    else:
        token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        raise HTTPException(status_code=400, detail="GitHub token not configured")
    
    return GitHubClient(token)

def get_cloudflare_client(db: Session = Depends(get_db)) -> CloudflareClient:
    """Get Cloudflare client with credentials from environment variables."""
    # Get credentials from database
    api_key_var = db.query(EnvironmentVariable).filter(
        EnvironmentVariable.key == "CLOUDFLARE_API_KEY"
    ).first()
    account_id_var = db.query(EnvironmentVariable).filter(
        EnvironmentVariable.key == "CLOUDFLARE_ACCOUNT_ID"
    ).first()
    
    api_key = api_key_var.get_value() if api_key_var else os.getenv("CLOUDFLARE_API_KEY")
    account_id = account_id_var.get_value() if account_id_var else os.getenv("CLOUDFLARE_ACCOUNT_ID")
    
    if not api_key or not account_id:
        raise HTTPException(status_code=400, detail="Cloudflare credentials not configured")
    
    return CloudflareClient(api_key, account_id)

@router.get("/repositories")
async def list_repositories(
    search: Optional[str] = None,
    per_page: int = 50,
    github_client: GitHubClient = Depends(get_github_client)
):
    """List GitHub repositories accessible to the user."""
    try:
        if search:
            repositories = await github_client.search_repositories(search, per_page)
        else:
            repositories = await github_client.list_repositories(per_page)
        
        return {
            "repositories": repositories,
            "total": len(repositories),
            "timestamp": datetime.now().timestamp()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repositories: {str(e)}")

@router.get("/repositories/{owner}/{repo}/branches")
async def get_repository_branches(
    owner: str,
    repo: str,
    github_client: GitHubClient = Depends(get_github_client)
):
    """Get branches for a specific repository."""
    try:
        branches = await github_client.get_repository_branches(owner, repo)
        return {
            "branches": branches,
            "total": len(branches),
            "repository": f"{owner}/{repo}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch branches: {str(e)}")

@router.post("/repositories/{owner}/{repo}/pin")
async def pin_repository_to_dashboard(
    owner: str,
    repo: str,
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    github_client: GitHubClient = Depends(get_github_client),
    cloudflare_client: CloudflareClient = Depends(get_cloudflare_client)
):
    """Pin a repository to the dashboard and set up webhook."""
    try:
        # Get repository details
        repositories = await github_client.list_repositories()
        repo_data = next((r for r in repositories if r["owner"] == owner and r["name"] == repo), None)
        
        if not repo_data:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        # Check if project already exists
        existing_project = db.query(Project).filter(
            Project.github_owner == owner,
            Project.github_repo == repo
        ).first()
        
        if existing_project:
            existing_project.is_pinned = True
            existing_project.updated_at = datetime.utcnow()
            db.commit()
            return {
                "success": True,
                "project_id": existing_project.id,
                "message": "Repository already pinned",
                "webhook_url": existing_project.webhook_url
            }
        
        # Get Cloudflare worker URL for webhook
        worker_url_var = db.query(EnvironmentVariable).filter(
            EnvironmentVariable.key == "CLOUDFLARE_WORKER_URL"
        ).first()
        
        if not worker_url_var:
            raise HTTPException(status_code=400, detail="Cloudflare worker URL not configured")
        
        webhook_url = f"{worker_url_var.get_value()}/webhook/{owner}/{repo}"
        
        # Set up GitHub webhook
        webhook_result = await github_client.setup_webhook(
            owner, repo, webhook_url, ["pull_request", "push", "issues"]
        )
        
        if not webhook_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to set up webhook")
        
        # Create project in database
        new_project = Project(
            name=repo_data["name"],
            description=repo_data.get("description", ""),
            github_owner=owner,
            github_repo=repo,
            github_branch=repo_data["default_branch"],
            webhook_url=webhook_url,
            webhook_id=webhook_result["webhook_id"],
            is_pinned=True,
            is_active=True,
            webhook_active=True,
            validation_enabled=request.get("validation_enabled", True),
            auto_merge_enabled=request.get("auto_merge_enabled", False),
            auto_confirm_plans=request.get("auto_confirm_plans", True)
        )
        
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        
        return {
            "success": True,
            "project_id": new_project.id,
            "message": "Repository pinned successfully",
            "webhook_url": webhook_url,
            "webhook_id": webhook_result["webhook_id"]
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to pin repository: {str(e)}")

@router.delete("/repositories/{owner}/{repo}/unpin")
async def unpin_repository_from_dashboard(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
    github_client: GitHubClient = Depends(get_github_client)
):
    """Unpin a repository from the dashboard."""
    try:
        # Find the project
        project = db.query(Project).filter(
            Project.github_owner == owner,
            Project.github_repo == repo
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Remove webhook if it exists
        if project.webhook_id:
            try:
                # Note: GitHub API doesn't have a direct way to delete webhooks via our client
                # This would need to be implemented in the GitHubClient
                pass
            except Exception as e:
                print(f"Warning: Failed to remove webhook: {e}")
        
        # Update project to unpinned
        project.is_pinned = False
        project.webhook_active = False
        project.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Repository unpinned successfully"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to unpin repository: {str(e)}")

@router.get("/pinned-repositories")
async def get_pinned_repositories(db: Session = Depends(get_db)):
    """Get all pinned repositories."""
    try:
        pinned_projects = db.query(Project).filter(
            Project.is_pinned == True
        ).all()
        
        projects_data = []
        for project in pinned_projects:
            projects_data.append({
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "github_owner": project.github_owner,
                "github_repo": project.github_repo,
                "github_branch": project.github_branch,
                "webhook_url": project.webhook_url,
                "webhook_active": project.webhook_active,
                "validation_enabled": project.validation_enabled,
                "auto_merge_enabled": project.auto_merge_enabled,
                "auto_confirm_plans": project.auto_confirm_plans,
                "is_active": project.is_active,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                "last_run_at": project.last_run_at.isoformat() if project.last_run_at else None,
                "total_runs": project.total_runs,
                "success_rate": project.success_rate,
                "current_agent_run": {
                    "status": project.current_run_status,
                    "pr_number": project.current_pr_number,
                    "pr_url": project.current_pr_url,
                    "progress_percentage": project.current_progress_percentage,
                    "current_step": project.current_step
                } if project.current_run_status else None
            })
        
        return {
            "projects": projects_data,
            "total": len(projects_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch pinned repositories: {str(e)}")

@router.post("/setup-webhook-worker")
async def setup_webhook_worker(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    cloudflare_client: CloudflareClient = Depends(get_cloudflare_client)
):
    """Set up the Cloudflare webhook worker."""
    try:
        dashboard_url = request.get("dashboard_url", "http://localhost:8000")
        worker_name = request.get("worker_name", "webhook-gateway")
        
        # Generate worker script
        worker_script = generate_webhook_worker_script(dashboard_url)
        
        # Deploy worker
        deployment_result = await cloudflare_client.deploy_webhook_worker(
            worker_name, worker_script
        )
        
        if deployment_result["success"]:
            # Update environment variable with worker URL
            worker_url_var = db.query(EnvironmentVariable).filter(
                EnvironmentVariable.key == "CLOUDFLARE_WORKER_URL"
            ).first()
            
            if worker_url_var:
                worker_url_var.set_value(deployment_result["worker_url"])
                worker_url_var.updated_at = datetime.utcnow()
            else:
                worker_url_var = EnvironmentVariable(
                    key="CLOUDFLARE_WORKER_URL",
                    category="cloudflare",
                    description="Cloudflare worker webhook URL",
                    sensitive=False
                )
                worker_url_var.set_value(deployment_result["worker_url"])
                db.add(worker_url_var)
            
            db.commit()
            
            return {
                "success": True,
                "worker_url": deployment_result["worker_url"],
                "worker_name": worker_name,
                "message": "Webhook worker deployed successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to deploy webhook worker")
            
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to setup webhook worker: {str(e)}")

@router.get("/pull-request/{owner}/{repo}/{pr_number}")
async def get_pull_request_details(
    owner: str,
    repo: str,
    pr_number: int,
    github_client: GitHubClient = Depends(get_github_client)
):
    """Get details of a specific pull request."""
    try:
        pr_details = await github_client.get_pull_request(owner, repo, pr_number)
        return {
            "success": True,
            "pull_request": pr_details
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch PR details: {str(e)}")

@router.post("/pull-request/{owner}/{repo}/{pr_number}/merge")
async def merge_pull_request(
    owner: str,
    repo: str,
    pr_number: int,
    request: Dict[str, Any],
    github_client: GitHubClient = Depends(get_github_client)
):
    """Merge a pull request."""
    try:
        merge_result = await github_client.merge_pull_request(
            owner, repo, pr_number,
            commit_title=request.get("commit_title"),
            commit_message=request.get("commit_message"),
            merge_method=request.get("merge_method", "merge")
        )
        
        return {
            "success": True,
            "merge_result": merge_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to merge PR: {str(e)}")

@router.post("/pull-request/{owner}/{repo}/{pr_number}/comment")
async def add_pr_comment(
    owner: str,
    repo: str,
    pr_number: int,
    request: Dict[str, Any],
    github_client: GitHubClient = Depends(get_github_client)
):
    """Add a comment to a pull request."""
    try:
        comment_body = request.get("body", "")
        if not comment_body:
            raise HTTPException(status_code=400, detail="Comment body is required")
        
        comment_result = await github_client.create_issue_comment(
            owner, repo, pr_number, comment_body
        )
        
        return {
            "success": True,
            "comment": comment_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add comment: {str(e)}")

@router.get("/test-connection")
async def test_github_connection(github_client: GitHubClient = Depends(get_github_client)):
    """Test GitHub API connection."""
    try:
        connection_result = await github_client.test_connection()
        return {
            "success": True,
            "connection": connection_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub connection failed: {str(e)}")
