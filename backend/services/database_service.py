"""
Database Service - Coordinates repository operations and business logic
"""

from typing import List, Optional, Dict, Any
import logging

from ..repositories.project_repository import ProjectRepository
from ..repositories.project_settings_repository import ProjectSettingsRepository
from ..repositories.project_secrets_repository import ProjectSecretsRepository
from ..models.project import Project, ProjectSettings, ProjectSecret

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service layer coordinating all database operations"""
    
    def __init__(self):
        self.project_repo = ProjectRepository()
        self.settings_repo = ProjectSettingsRepository()
        self.secrets_repo = ProjectSecretsRepository()
    
    async def create_project_with_settings(
        self, 
        project_data: Dict[str, Any], 
        settings_data: Dict[str, Any]
    ) -> Project:
        """Create a project with its settings in a transaction"""
        try:
            # Create project
            project = self.project_repo.create(project_data)
            
            # Create settings
            settings_data['project_id'] = project.id
            settings = self.settings_repo.create(settings_data)
            
            # Attach settings to project
            project.settings = settings
            
            logger.info(f"Created project {project.id} with settings")
            return project
            
        except Exception as e:
            logger.error(f"Error creating project with settings: {e}")
            raise
    
    async def get_project_full_config(self, project_id: int) -> Dict[str, Any]:
        """Get complete project configuration including settings and secrets"""
        try:
            # Get project
            project = self.project_repo.get_by_id(project_id)
            if not project:
                raise Exception(f"Project {project_id} not found")
            
            # Get settings
            settings = self.settings_repo.get_by_project_id(project_id)
            
            # Get secrets (without decrypted values for security)
            secrets = self.secrets_repo.get_by_project_id(project_id, decrypt=False)
            
            return {
                'project': project,
                'settings': settings,
                'secrets': secrets
            }
            
        except Exception as e:
            logger.error(f"Error getting project configuration {project_id}: {e}")
            raise
    
    async def update_project_secrets(
        self, 
        project_id: int, 
        secrets: List[Dict[str, str]]
    ) -> bool:
        """Update all secrets for a project"""
        try:
            # Verify project exists
            project = self.project_repo.get_by_id(project_id)
            if not project:
                raise Exception(f"Project {project_id} not found")
            
            # Update secrets
            self.secrets_repo.update_project_secrets(project_id, secrets)
            
            logger.info(f"Updated {len(secrets)} secrets for project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating secrets for project {project_id}: {e}")
            raise
    
    async def get_projects(self) -> List[Project]:
        """Get all projects with their settings"""
        try:
            projects = self.project_repo.list_all()
            
            # Attach settings to each project
            for project in projects:
                settings = self.settings_repo.get_by_project_id(project.id)
                project.settings = settings
            
            return projects
            
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            raise
    
    async def get_active_projects(self) -> List[Project]:
        """Get active projects with their settings"""
        try:
            projects = self.project_repo.list_active_projects()
            
            # Attach settings to each project
            for project in projects:
                settings = self.settings_repo.get_by_project_id(project.id)
                project.settings = settings
            
            return projects
            
        except Exception as e:
            logger.error(f"Error getting active projects: {e}")
            raise
    
    async def get_project(self, project_id: int) -> Optional[Project]:
        """Get project by ID with settings"""
        try:
            project = self.project_repo.get_by_id(project_id)
            if not project:
                return None
            
            # Attach settings
            settings = self.settings_repo.get_by_project_id(project_id)
            project.settings = settings
            
            return project
            
        except Exception as e:
            logger.error(f"Error getting project {project_id}: {e}")
            raise
    
    async def update_project(self, project_id: int, data: Dict[str, Any]) -> Optional[Project]:
        """Update project"""
        try:
            project = self.project_repo.update(project_id, data)
            if not project:
                return None
            
            # Attach settings
            settings = self.settings_repo.get_by_project_id(project_id)
            project.settings = settings
            
            return project
            
        except Exception as e:
            logger.error(f"Error updating project {project_id}: {e}")
            raise
    
    async def update_project_settings(
        self, 
        project_id: int, 
        settings_data: Dict[str, Any]
    ) -> Optional[ProjectSettings]:
        """Update project settings"""
        try:
            # Check if settings exist
            existing_settings = self.settings_repo.get_by_project_id(project_id)
            
            if existing_settings:
                # Update existing settings
                return self.settings_repo.update_by_project_id(project_id, settings_data)
            else:
                # Create new settings
                settings_data['project_id'] = project_id
                return self.settings_repo.create(settings_data)
            
        except Exception as e:
            logger.error(f"Error updating settings for project {project_id}: {e}")
            raise
    
    async def delete_project(self, project_id: int) -> bool:
        """Delete project and all related data"""
        try:
            # Delete secrets first (due to foreign key constraints)
            self.secrets_repo.delete_by_project_id(project_id)
            
            # Delete settings
            self.settings_repo.delete_by_project_id(project_id)
            
            # Delete project
            deleted = self.project_repo.delete(project_id)
            
            if deleted:
                logger.info(f"Deleted project {project_id} and all related data")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {e}")
            raise
    
    async def get_secret_value(self, project_id: int, key_name: str) -> Optional[str]:
        """Get decrypted secret value (for internal use only)"""
        try:
            return self.secrets_repo.get_secret_value(project_id, key_name)
        except Exception as e:
            logger.error(f"Error getting secret value {project_id}/{key_name}: {e}")
            raise

