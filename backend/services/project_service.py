"""
Project management service
"""
import os
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
import structlog

from backend.database import get_db_session
from backend.models.project import Project, ProjectSettings, ValidationRun
from backend.models.agent_run import AgentRun
from backend.services.github_service import github_service
from backend.services.secrets_manager import encrypt_secrets, decrypt_secrets

logger = structlog.get_logger(__name__)


class ProjectService:
    """Service for managing projects and their settings"""
    
    def __init__(self):
        self.github_service = github_service
    
    async def get_github_repositories(self) -> List[Dict[str, Any]]:
        """Get all GitHub repositories for the user"""
        try:
            repos = await self.github_service.get_user_repositories()
            
            # Transform to our format
            formatted_repos = []
            for repo in repos:
                formatted_repos.append({
                    "id": repo["id"],
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "description": repo.get("description"),
                    "owner": repo["owner"]["login"],
                    "url": repo["html_url"],
                    "clone_url": repo["clone_url"],
                    "default_branch": repo["default_branch"],
                    "private": repo["private"],
                    "updated_at": repo["updated_at"]
                })
            
            return formatted_repos
            
        except Exception as e:
            logger.error("Error fetching GitHub repositories", error=str(e))
            raise
    
    async def add_project_to_dashboard(self, github_repo_data: Dict[str, Any]) -> Project:
        """Add a GitHub repository as a project to the dashboard"""
        async with get_db_session() as session:
            try:
                # Check if project already exists
                existing_project = session.query(Project).filter(
                    Project.github_id == github_repo_data["id"]
                ).first()
                
                if existing_project:
                    logger.info("Project already exists", project_id=existing_project.id)
                    return existing_project
                
                # Create new project
                project = Project(
                    github_id=github_repo_data["id"],
                    name=github_repo_data["name"],
                    full_name=github_repo_data["full_name"],
                    description=github_repo_data.get("description"),
                    github_owner=github_repo_data["owner"],
                    github_repo=github_repo_data["name"],
                    github_branch=github_repo_data.get("default_branch", "main"),
                    github_url=github_repo_data["url"],
                    webhook_url=os.getenv("CLOUDFLARE_WORKER_URL", "https://webhook-gateway.pixeliumperfecto.workers.dev")
                )
                
                session.add(project)
                await session.commit()
                await session.refresh(project)
                
                # Create default project settings
                settings = ProjectSettings(
                    project_id=project.id,
                    planning_statement="You are an expert software engineer. Please analyze the request and provide a detailed implementation plan.",
                    secrets={}
                )
                
                session.add(settings)
                await session.commit()
                
                # Set up GitHub webhook
                try:
                    webhook = await self.github_service.set_repository_webhook(
                        project.github_owner,
                        project.github_repo,
                        project.webhook_url
                    )
                    
                    project.webhook_active = True
                    await session.commit()
                    
                    logger.info("Project added with webhook", 
                              project_id=project.id, webhook_id=webhook.get("id"))
                    
                except Exception as webhook_error:
                    logger.warning("Failed to set webhook, project added without webhook",
                                 project_id=project.id, error=str(webhook_error))
                
                return project
                
            except Exception as e:
                await session.rollback()
                logger.error("Error adding project to dashboard", error=str(e))
                raise
    
    async def get_dashboard_projects(self) -> List[Dict[str, Any]]:
        """Get all projects on the dashboard"""
        async with get_db_session() as session:
            try:
                projects = session.query(Project).filter(
                    Project.is_active == True
                ).order_by(Project.updated_at.desc()).all()
                
                result = []
                for project in projects:
                    # Get current agent run if any
                    current_run = session.query(AgentRun).filter(
                        and_(
                            AgentRun.project_id == project.id,
                            AgentRun.status.in_(["pending", "running", "waiting_for_input"])
                        )
                    ).order_by(AgentRun.created_at.desc()).first()
                    
                    project_data = {
                        "id": project.id,
                        "github_id": project.github_id,
                        "name": project.name,
                        "full_name": project.full_name,
                        "description": project.description,
                        "github_owner": project.github_owner,
                        "github_repo": project.github_repo,
                        "github_branch": project.github_branch,
                        "github_url": project.github_url,
                        "webhook_active": project.webhook_active,
                        "webhook_url": project.webhook_url,
                        "auto_merge_enabled": project.auto_merge_enabled,
                        "auto_confirm_plans": project.auto_confirm_plans,
                        "auto_merge_threshold": project.auto_merge_threshold,
                        "status": project.status,
                        "validation_enabled": project.validation_enabled,
                        "has_repository_rules": project.has_repository_rules,
                        "has_setup_commands": project.has_setup_commands,
                        "has_secrets": project.has_secrets,
                        "has_planning_statement": project.has_planning_statement,
                        "total_runs": project.total_runs,
                        "success_rate": project.success_rate,
                        "created_at": project.created_at.isoformat(),
                        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                        "current_agent_run": None
                    }
                    
                    if current_run:
                        project_data["current_agent_run"] = {
                            "id": current_run.id,
                            "status": current_run.status.value,
                            "progress_percentage": current_run.progress_percentage,
                            "run_type": current_run.run_type.value,
                            "target": current_run.target,
                            "pr_url": current_run.pr_url,
                            "pr_number": current_run.pr_number
                        }
                    
                    result.append(project_data)
                
                return result
                
            except Exception as e:
                logger.error("Error fetching dashboard projects", error=str(e))
                raise
    
    async def remove_project_from_dashboard(self, project_id: int) -> bool:
        """Remove a project from the dashboard"""
        async with get_db_session() as session:
            try:
                project = session.query(Project).filter(Project.id == project_id).first()
                if not project:
                    return False
                
                # Remove webhook if active
                if project.webhook_active:
                    try:
                        webhook = await self.github_service.get_repository_webhook(
                            project.github_owner,
                            project.github_repo,
                            project.webhook_url
                        )
                        
                        if webhook:
                            await self.github_service.remove_repository_webhook(
                                project.github_owner,
                                project.github_repo,
                                webhook["id"]
                            )
                    except Exception as webhook_error:
                        logger.warning("Failed to remove webhook", 
                                     project_id=project_id, error=str(webhook_error))
                
                # Soft delete - mark as inactive
                project.is_active = False
                await session.commit()
                
                logger.info("Project removed from dashboard", project_id=project_id)
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error("Error removing project from dashboard", 
                           project_id=project_id, error=str(e))
                raise
    
    async def get_project_settings(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get project settings"""
        async with get_db_session() as session:
            try:
                project = session.query(Project).filter(Project.id == project_id).first()
                if not project:
                    return None
                
                settings = session.query(ProjectSettings).filter(
                    ProjectSettings.project_id == project_id
                ).first()
                
                if not settings:
                    # Create default settings
                    settings = ProjectSettings(
                        project_id=project_id,
                        planning_statement="You are an expert software engineer. Please analyze the request and provide a detailed implementation plan.",
                        secrets={}
                    )
                    session.add(settings)
                    await session.commit()
                    await session.refresh(settings)
                
                # Decrypt secrets
                decrypted_secrets = {}
                if settings.secrets:
                    try:
                        decrypted_secrets = decrypt_secrets(settings.secrets)
                    except Exception as decrypt_error:
                        logger.warning("Failed to decrypt secrets", 
                                     project_id=project_id, error=str(decrypt_error))
                
                return {
                    "project_id": project_id,
                    "repository_rules": settings.repository_rules,
                    "setup_commands": settings.setup_commands,
                    "setup_branch": settings.setup_branch,
                    "planning_statement": settings.planning_statement,
                    "secrets": decrypted_secrets,
                    "validation_timeout": settings.validation_timeout,
                    "max_validation_retries": settings.max_validation_retries,
                    "deployment_commands": settings.deployment_commands,
                    "health_check_url": settings.health_check_url
                }
                
            except Exception as e:
                logger.error("Error fetching project settings", 
                           project_id=project_id, error=str(e))
                raise
    
    async def update_project_settings(self, project_id: int, 
                                    settings_data: Dict[str, Any]) -> bool:
        """Update project settings"""
        async with get_db_session() as session:
            try:
                project = session.query(Project).filter(Project.id == project_id).first()
                if not project:
                    return False
                
                settings = session.query(ProjectSettings).filter(
                    ProjectSettings.project_id == project_id
                ).first()
                
                if not settings:
                    settings = ProjectSettings(project_id=project_id)
                    session.add(settings)
                
                # Update settings
                if "repository_rules" in settings_data:
                    settings.repository_rules = settings_data["repository_rules"]
                    project.has_repository_rules = bool(settings_data["repository_rules"])
                
                if "setup_commands" in settings_data:
                    settings.setup_commands = settings_data["setup_commands"]
                    project.has_setup_commands = bool(settings_data["setup_commands"])
                
                if "setup_branch" in settings_data:
                    settings.setup_branch = settings_data["setup_branch"]
                
                if "planning_statement" in settings_data:
                    settings.planning_statement = settings_data["planning_statement"]
                    project.has_planning_statement = bool(settings_data["planning_statement"])
                
                if "secrets" in settings_data:
                    # Encrypt secrets before storing
                    encrypted_secrets = encrypt_secrets(settings_data["secrets"])
                    settings.secrets = encrypted_secrets
                    project.has_secrets = bool(settings_data["secrets"])
                
                if "validation_timeout" in settings_data:
                    settings.validation_timeout = settings_data["validation_timeout"]
                
                if "max_validation_retries" in settings_data:
                    settings.max_validation_retries = settings_data["max_validation_retries"]
                
                if "deployment_commands" in settings_data:
                    settings.deployment_commands = settings_data["deployment_commands"]
                
                if "health_check_url" in settings_data:
                    settings.health_check_url = settings_data["health_check_url"]
                
                await session.commit()
                
                logger.info("Project settings updated", project_id=project_id)
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error("Error updating project settings", 
                           project_id=project_id, error=str(e))
                raise
    
    async def update_project_config(self, project_id: int, 
                                  config_data: Dict[str, Any]) -> bool:
        """Update project configuration (auto-merge, auto-confirm, etc.)"""
        async with get_db_session() as session:
            try:
                project = session.query(Project).filter(Project.id == project_id).first()
                if not project:
                    return False
                
                if "auto_merge_enabled" in config_data:
                    project.auto_merge_enabled = config_data["auto_merge_enabled"]
                
                if "auto_confirm_plans" in config_data:
                    project.auto_confirm_plans = config_data["auto_confirm_plans"]
                
                if "auto_merge_threshold" in config_data:
                    project.auto_merge_threshold = config_data["auto_merge_threshold"]
                
                if "validation_enabled" in config_data:
                    project.validation_enabled = config_data["validation_enabled"]
                
                await session.commit()
                
                logger.info("Project configuration updated", project_id=project_id)
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error("Error updating project configuration", 
                           project_id=project_id, error=str(e))
                raise
    
    async def get_repository_branches(self, project_id: int) -> List[Dict[str, Any]]:
        """Get branches for a project's repository"""
        async with get_db_session() as session:
            try:
                project = session.query(Project).filter(Project.id == project_id).first()
                if not project:
                    return []
                
                branches = await self.github_service.get_repository_branches(
                    project.github_owner,
                    project.github_repo
                )
                
                return [{"name": branch["name"], "sha": branch["commit"]["sha"]} 
                       for branch in branches]
                
            except Exception as e:
                logger.error("Error fetching repository branches", 
                           project_id=project_id, error=str(e))
                return []


# Global instance
project_service = ProjectService()

