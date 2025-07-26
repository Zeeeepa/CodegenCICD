"""
Project service for managing projects and their configurations
"""
import structlog
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from backend.models.project import Project
from backend.models.configuration import Configuration
from backend.integrations.github_client import GitHubClient
from backend.integrations.cloudflare_client import CloudflareClient
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class ProjectService:
    """Service for managing projects and their configurations"""
    
    def __init__(self):
        self.github_client = GitHubClient()
        self.cloudflare_client = CloudflareClient()
    
    async def create_project(
        self,
        db: AsyncSession,
        name: str,
        repository_url: str,
        description: Optional[str] = None,
        default_branch: str = "main",
        auto_merge_enabled: bool = False,
        created_by: str = "system"
    ) -> Project:
        """Create a new project with webhook setup"""
        logger.info("Creating project", name=name, repository_url=repository_url)
        
        # Validate repository URL
        if not repository_url.startswith("https://github.com/"):
            raise ValueError("Only GitHub repositories are supported")
        
        # Extract owner and repo from URL
        parts = repository_url.replace("https://github.com/", "").split("/")
        if len(parts) != 2:
            raise ValueError("Invalid GitHub repository URL format")
        
        owner, repo = parts
        
        # Verify repository exists and is accessible
        try:
            repo_info = await self.github_client.get_repository(owner, repo)
            logger.info("Repository verified", owner=owner, repo=repo)
        except Exception as e:
            logger.error("Failed to verify repository", owner=owner, repo=repo, error=str(e))
            raise ValueError(f"Repository not accessible: {str(e)}")
        
        # Generate webhook URL
        webhook_url = f"{settings.cloudflare_worker_url}/github"
        
        # Create project
        project = Project(
            name=name,
            description=description,
            repository_url=repository_url,
            default_branch=default_branch,
            webhook_url=webhook_url,
            auto_merge_enabled=auto_merge_enabled,
            created_by=created_by
        )
        
        db.add(project)
        await db.flush()  # Get the project ID
        
        # Create default configuration
        config = Configuration(
            project_id=project.id,
            repository_rules="",
            setup_commands="",
            planning_statement="",
            secrets={}
        )
        
        db.add(config)
        await db.commit()
        await db.refresh(project)
        
        # Set up GitHub webhook
        try:
            webhook_id = await self.github_client.create_webhook(
                owner=owner,
                repo=repo,
                webhook_url=webhook_url,
                events=["pull_request", "push"]
            )
            logger.info("GitHub webhook created", webhook_id=webhook_id, project_id=project.id)
        except Exception as e:
            logger.warning("Failed to create GitHub webhook", project_id=project.id, error=str(e))
            # Don't fail project creation if webhook setup fails
        
        logger.info("Project created successfully", project_id=project.id)
        return project
    
    async def update_project(
        self,
        db: AsyncSession,
        project_id: str,
        **updates
    ) -> Optional[Project]:
        """Update a project"""
        logger.info("Updating project", project_id=project_id, updates=list(updates.keys()))
        
        # Check if project exists
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            return None
        
        # Apply updates
        if updates:
            await db.execute(
                update(Project)
                .where(Project.id == project_id)
                .values(**updates)
            )
            await db.commit()
            await db.refresh(project)
        
        logger.info("Project updated", project_id=project_id)
        return project
    
    async def delete_project(
        self,
        db: AsyncSession,
        project_id: str
    ) -> bool:
        """Delete a project and clean up resources"""
        logger.info("Deleting project", project_id=project_id)
        
        # Get project
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            return False
        
        # Clean up GitHub webhook if possible
        try:
            parts = project.repository_url.replace("https://github.com/", "").split("/")
            if len(parts) == 2:
                owner, repo = parts
                await self.github_client.delete_webhook(owner, repo, project.webhook_url)
                logger.info("GitHub webhook deleted", project_id=project_id)
        except Exception as e:
            logger.warning("Failed to delete GitHub webhook", project_id=project_id, error=str(e))
        
        # Delete project (cascade will handle related records)
        await db.execute(delete(Project).where(Project.id == project_id))
        await db.commit()
        
        logger.info("Project deleted", project_id=project_id)
        return True
    
    async def get_project(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Optional[Project]:
        """Get a project by ID"""
        result = await db.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()
    
    async def list_projects(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10
    ) -> List[Project]:
        """List projects with pagination"""
        result = await db.execute(
            select(Project)
            .offset(skip)
            .limit(limit)
            .order_by(Project.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_project_configuration(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Optional[Configuration]:
        """Get project configuration"""
        result = await db.execute(
            select(Configuration).where(Configuration.project_id == project_id)
        )
        return result.scalar_one_or_none()
    
    async def update_project_configuration(
        self,
        db: AsyncSession,
        project_id: str,
        repository_rules: Optional[str] = None,
        setup_commands: Optional[str] = None,
        planning_statement: Optional[str] = None,
        secrets: Optional[Dict[str, str]] = None
    ) -> Configuration:
        """Update project configuration"""
        logger.info("Updating project configuration", project_id=project_id)
        
        # Get or create configuration
        result = await db.execute(
            select(Configuration).where(Configuration.project_id == project_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            config = Configuration(project_id=project_id)
            db.add(config)
        
        # Update fields
        if repository_rules is not None:
            config.repository_rules = repository_rules
        if setup_commands is not None:
            config.setup_commands = setup_commands
        if planning_statement is not None:
            config.planning_statement = planning_statement
        if secrets is not None:
            # Encrypt secrets before storing
            config.secrets = secrets
        
        await db.commit()
        await db.refresh(config)
        
        logger.info("Project configuration updated", project_id=project_id)
        return config
    
    async def test_setup_commands(
        self,
        db: AsyncSession,
        project_id: str,
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Test project setup commands in sandbox"""
        logger.info("Testing setup commands", project_id=project_id, branch=branch)
        
        # Get project and configuration
        project = await self.get_project(db, project_id)
        if not project:
            raise ValueError("Project not found")
        
        config = await self.get_project_configuration(db, project_id)
        if not config or not config.setup_commands:
            raise ValueError("No setup commands configured")
        
        # Use validation service to test commands
        from backend.services.validation_service import ValidationService
        validation_service = ValidationService()
        
        try:
            # Create a test validation run
            result = await validation_service.test_setup_commands(
                project_id=project_id,
                repository_url=project.repository_url,
                branch_name=branch or project.default_branch,
                setup_commands=config.setup_commands,
                secrets=config.secrets or {}
            )
            
            logger.info("Setup commands test completed", project_id=project_id, success=result.get("success"))
            return result
            
        except Exception as e:
            logger.error("Setup commands test failed", project_id=project_id, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "logs": []
            }
    
    async def get_project_statistics(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Dict[str, Any]:
        """Get project statistics"""
        from backend.models.agent_run import AgentRun
        from backend.models.validation import Validation
        
        # Count agent runs
        agent_runs_result = await db.execute(
            select(AgentRun).where(AgentRun.project_id == project_id)
        )
        agent_runs = agent_runs_result.scalars().all()
        
        # Count validations
        validations_result = await db.execute(
            select(Validation).where(Validation.project_id == project_id)
        )
        validations = validations_result.scalars().all()
        
        # Calculate statistics
        total_agent_runs = len(agent_runs)
        completed_agent_runs = len([r for r in agent_runs if r.status == "completed"])
        failed_agent_runs = len([r for r in agent_runs if r.status == "failed"])
        
        total_validations = len(validations)
        successful_validations = len([v for v in validations if v.status == "completed"])
        
        return {
            "agent_runs": {
                "total": total_agent_runs,
                "completed": completed_agent_runs,
                "failed": failed_agent_runs,
                "success_rate": completed_agent_runs / total_agent_runs if total_agent_runs > 0 else 0
            },
            "validations": {
                "total": total_validations,
                "successful": successful_validations,
                "success_rate": successful_validations / total_validations if total_validations > 0 else 0
            }
        }

