"""
Database service layer coordinating repository operations
"""
from typing import Dict, Any, List, Optional
import logging
from contextlib import asynccontextmanager

from database.connection_manager import DatabaseManager, get_database_manager
from repositories import (
    RepositoryFactory, 
    get_repository_factory,
    ProjectRepository,
    ProjectSettingsRepository,
    ProjectSecretsRepository
)
from models import Project, ProjectSettings, ProjectSecret
from errors.exceptions import DatabaseError, ValidationError, SecurityError

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service layer coordinating database operations across repositories"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or get_database_manager()
        self.repo_factory = RepositoryFactory(self.db_manager)
        
        # Repository shortcuts
        self.projects = self.repo_factory.project_repository
        self.settings = self.repo_factory.project_settings_repository
        self.secrets = self.repo_factory.project_secrets_repository
    
    async def create_project_with_settings(
        self, 
        project_data: Dict[str, Any], 
        settings_data: Optional[Dict[str, Any]] = None,
        secrets_data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a project with optional settings and secrets in a transaction"""
        try:
            with self.db_manager.transaction():
                # Create project
                project = self.projects.create(project_data)
                
                # Create settings if provided
                project_settings = None
                if settings_data:
                    settings_data['project_id'] = project.id
                    project_settings = self.settings.create(settings_data)
                
                # Create secrets if provided
                project_secrets = []
                if secrets_data:
                    for key_name, value in secrets_data.items():
                        secret_data = {
                            'project_id': project.id,
                            'key_name': key_name,
                            'value': value
                        }
                        secret = self.secrets.create(secret_data)
                        project_secrets.append(secret)
                
                logger.info(f"Created project {project.id} with settings and {len(project_secrets)} secrets")
                
                return {
                    'project': project,
                    'settings': project_settings,
                    'secrets': project_secrets
                }
                
        except Exception as e:
            logger.error(f"Failed to create project with settings: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError, SecurityError)):
                raise
            raise DatabaseError(f"Project creation failed: {str(e)}")
    
    async def get_project_full_config(self, project_id: int) -> Dict[str, Any]:
        """Get complete project configuration including settings and secrets"""
        try:
            # Get project
            project = self.projects.get_by_id(project_id)
            if not project:
                raise ValidationError(f"Project {project_id} not found")
            
            # Get settings
            settings = self.settings.get_by_project_id(project_id)
            
            # Get secrets (encrypted values only for security)
            secrets = self.secrets.get_by_project_id(project_id)
            
            return {
                'project': project,
                'settings': settings,
                'secrets': [
                    {
                        'id': secret.id,
                        'key_name': secret.key_name,
                        'created_at': secret.created_at
                    }
                    for secret in secrets
                ],
                'secret_count': len(secrets)
            }
            
        except Exception as e:
            logger.error(f"Failed to get project full config {project_id}: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError)):
                raise
            raise DatabaseError(f"Failed to get project configuration: {str(e)}")
    
    async def get_project_secrets_decrypted(self, project_id: int) -> Dict[str, str]:
        """Get decrypted secrets for a project (use with caution)"""
        try:
            # Verify project exists
            project = self.projects.get_by_id(project_id)
            if not project:
                raise ValidationError(f"Project {project_id} not found")
            
            # Get decrypted secrets
            decrypted_secrets = self.secrets.get_decrypted_secrets(project_id)
            
            logger.info(f"Retrieved {len(decrypted_secrets)} decrypted secrets for project {project_id}")
            return decrypted_secrets
            
        except Exception as e:
            logger.error(f"Failed to get decrypted secrets for project {project_id}: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError, SecurityError)):
                raise
            raise DatabaseError(f"Failed to get project secrets: {str(e)}")
    
    async def update_project_configuration(
        self,
        project_id: int,
        project_data: Optional[Dict[str, Any]] = None,
        settings_data: Optional[Dict[str, Any]] = None,
        secrets_data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Update project configuration including settings and secrets"""
        try:
            with self.db_manager.transaction():
                # Verify project exists
                project = self.projects.get_by_id(project_id)
                if not project:
                    raise ValidationError(f"Project {project_id} not found")
                
                # Update project if data provided
                if project_data:
                    project = self.projects.update(project_id, project_data)
                
                # Update settings if data provided
                settings = None
                if settings_data:
                    settings = self.settings.update_by_project_id(project_id, settings_data)
                
                # Update secrets if data provided
                updated_secrets = []
                if secrets_data:
                    updated_secrets = self.secrets.bulk_update_secrets(project_id, secrets_data)
                
                logger.info(f"Updated project {project_id} configuration")
                
                return {
                    'project': project,
                    'settings': settings,
                    'secrets_updated': len(updated_secrets)
                }
                
        except Exception as e:
            logger.error(f"Failed to update project configuration {project_id}: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError, SecurityError)):
                raise
            raise DatabaseError(f"Project configuration update failed: {str(e)}")
    
    async def delete_project_complete(self, project_id: int) -> bool:
        """Delete project and all related data"""
        try:
            with self.db_manager.transaction():
                # Verify project exists
                project = self.projects.get_by_id(project_id)
                if not project:
                    return False
                
                # Delete secrets first (due to foreign key constraints)
                secrets_deleted = self.secrets.delete_by_project_id(project_id)
                
                # Delete settings
                settings_deleted = self.settings.delete_by_project_id(project_id)
                
                # Delete project (soft delete)
                project_deleted = self.projects.delete(project_id)
                
                logger.info(f"Deleted project {project_id} with {secrets_deleted} secrets and settings")
                return project_deleted
                
        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {str(e)}")
            raise DatabaseError(f"Project deletion failed: {str(e)}")
    
    async def get_projects_list(
        self, 
        limit: int = 100, 
        offset: int = 0, 
        active_only: bool = True
    ) -> Dict[str, Any]:
        """Get paginated list of projects with basic info"""
        try:
            if active_only:
                projects = self.projects.list_active_projects()
                total_count = self.projects.get_project_count()
            else:
                projects = self.projects.list_all_projects(limit, offset)
                # For simplicity, use active count as total (could be enhanced)
                total_count = self.projects.get_project_count()
            
            # Apply pagination to active projects if needed
            if active_only and (limit or offset):
                start_idx = offset
                end_idx = offset + limit if limit else len(projects)
                projects = projects[start_idx:end_idx]
            
            return {
                'projects': projects,
                'total_count': total_count,
                'limit': limit,
                'offset': offset
            }
            
        except Exception as e:
            logger.error(f"Failed to get projects list: {str(e)}")
            raise DatabaseError(f"Failed to get projects list: {str(e)}")
    
    async def search_projects(self, search_term: str, limit: int = 50) -> List[Project]:
        """Search projects by name or GitHub repository"""
        try:
            projects = self.projects.search_projects(search_term, limit)
            logger.info(f"Found {len(projects)} projects matching '{search_term}'")
            return projects
            
        except Exception as e:
            logger.error(f"Failed to search projects: {str(e)}")
            raise DatabaseError(f"Project search failed: {str(e)}")
    
    async def get_project_by_github_repo(self, owner: str, repo: str) -> Optional[Project]:
        """Get project by GitHub owner and repository"""
        try:
            project = self.projects.get_by_github_repo(owner, repo)
            return project
            
        except Exception as e:
            logger.error(f"Failed to get project by GitHub repo {owner}/{repo}: {str(e)}")
            raise DatabaseError(f"Failed to get project: {str(e)}")
    
    async def update_project_webhook(self, project_id: int, webhook_url: str) -> bool:
        """Update webhook URL for a project"""
        try:
            success = self.projects.update_webhook_url(project_id, webhook_url)
            if success:
                logger.info(f"Updated webhook URL for project {project_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to update webhook for project {project_id}: {str(e)}")
            raise DatabaseError(f"Webhook update failed: {str(e)}")
    
    async def get_project_planning_context(self, project_id: int) -> Dict[str, Any]:
        """Get project context for agent run planning"""
        try:
            # Get project
            project = self.projects.get_by_id(project_id)
            if not project:
                raise ValidationError(f"Project {project_id} not found")
            
            # Get settings
            settings = self.settings.get_by_project_id(project_id)
            
            # Get decrypted secrets for context
            secrets = self.secrets.get_decrypted_secrets(project_id)
            
            context = {
                'project_name': project.name,
                'github_owner': project.github_owner,
                'github_repo': project.github_repo,
                'planning_statement': settings.planning_statement if settings else None,
                'repository_rules': settings.repository_rules if settings else None,
                'setup_commands': settings.setup_commands if settings else None,
                'branch_name': settings.branch_name if settings else 'main',
                'secrets': secrets,
                'auto_confirm_plans': project.auto_confirm_plans
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get planning context for project {project_id}: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError, SecurityError)):
                raise
            raise DatabaseError(f"Failed to get project context: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            # Test basic connectivity
            test_query = "SELECT 1 as test"
            result = self.db_manager.execute_query(test_query)
            
            # Get basic stats
            project_count = self.projects.get_project_count()
            
            return {
                'status': 'healthy',
                'database_connected': len(result) > 0,
                'project_count': project_count,
                'connection_pool_stats': self.db_manager.get_connection_stats()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'database_connected': False
            }


# Global database service instance
_database_service: Optional[DatabaseService] = None


def get_database_service() -> DatabaseService:
    """Get the global database service instance"""
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
    return _database_service


def initialize_database_service(db_manager: Optional[DatabaseManager] = None) -> DatabaseService:
    """Initialize database service with custom database manager"""
    global _database_service
    _database_service = DatabaseService(db_manager)
    return _database_service

