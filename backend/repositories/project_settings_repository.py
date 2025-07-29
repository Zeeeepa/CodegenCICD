"""
Project settings repository implementation using foundation database layer
"""
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from database.base import BaseRepository
from database.connection_manager import DatabaseManager
from models import ProjectSettings
from errors.exceptions import DatabaseError, ValidationError

logger = logging.getLogger(__name__)


class ProjectSettingsRepository(BaseRepository[ProjectSettings]):
    """Repository for project settings CRUD operations"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(ProjectSettings, "project_settings", db_manager)
    
    def create(self, data: Dict[str, Any]) -> ProjectSettings:
        """Create new project settings"""
        try:
            # Validate required fields
            if not data.get('project_id'):
                raise ValidationError("Missing required field: project_id")
            
            # Check if settings already exist for this project
            existing = self.get_by_project_id(data['project_id'])
            if existing:
                raise ValidationError(f"Settings already exist for project {data['project_id']}")
            
            # Set timestamps
            now = datetime.utcnow()
            data['created_at'] = now
            data['updated_at'] = now
            
            # Execute insert
            query = """
                INSERT INTO project_settings (project_id, planning_statement, repository_rules, 
                                            setup_commands, branch_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                data['project_id'],
                data.get('planning_statement'),
                data.get('repository_rules'),
                data.get('setup_commands'),
                data.get('branch_name', 'main'),
                data['created_at'],
                data['updated_at']
            )
            
            settings_id = self.db_manager.execute_command(query, params)
            
            # Return created settings
            created_settings = self.get_by_id(settings_id)
            if not created_settings:
                raise DatabaseError("Failed to retrieve created project settings")
            
            logger.info(f"Created project settings {settings_id} for project {data['project_id']}")
            return created_settings
            
        except Exception as e:
            logger.error(f"Failed to create project settings: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError)):
                raise
            raise DatabaseError(f"Project settings creation failed: {str(e)}")
    
    def get_by_id(self, settings_id: int) -> Optional[ProjectSettings]:
        """Get project settings by ID"""
        try:
            query = "SELECT * FROM project_settings WHERE id = ?"
            results = self.db_manager.execute_query(query, (settings_id,))
            
            if not results:
                return None
            
            return ProjectSettings(**results[0])
            
        except Exception as e:
            logger.error(f"Failed to get project settings {settings_id}: {str(e)}")
            raise DatabaseError(f"Failed to retrieve project settings: {str(e)}")
    
    def get_by_project_id(self, project_id: int) -> Optional[ProjectSettings]:
        """Get project settings by project ID"""
        try:
            query = "SELECT * FROM project_settings WHERE project_id = ?"
            results = self.db_manager.execute_query(query, (project_id,))
            
            if not results:
                return None
            
            return ProjectSettings(**results[0])
            
        except Exception as e:
            logger.error(f"Failed to get project settings for project {project_id}: {str(e)}")
            raise DatabaseError(f"Failed to retrieve project settings: {str(e)}")
    
    def update(self, settings_id: int, data: Dict[str, Any]) -> Optional[ProjectSettings]:
        """Update project settings"""
        try:
            # Get existing settings
            existing = self.get_by_id(settings_id)
            if not existing:
                return None
            
            # Set update timestamp
            data['updated_at'] = datetime.utcnow()
            
            # Build update query dynamically
            update_fields = []
            params = []
            
            for field, value in data.items():
                if field in ['planning_statement', 'repository_rules', 'setup_commands', 
                           'branch_name', 'updated_at']:
                    update_fields.append(f"{field} = ?")
                    params.append(value)
            
            if not update_fields:
                return existing  # No valid fields to update
            
            params.append(settings_id)
            query = f"UPDATE project_settings SET {', '.join(update_fields)} WHERE id = ?"
            
            rows_affected = self.db_manager.execute_command(query, tuple(params))
            
            if rows_affected == 0:
                return None
            
            # Return updated settings
            updated_settings = self.get_by_id(settings_id)
            logger.info(f"Updated project settings {settings_id}")
            return updated_settings
            
        except Exception as e:
            logger.error(f"Failed to update project settings {settings_id}: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError)):
                raise
            raise DatabaseError(f"Project settings update failed: {str(e)}")
    
    def update_by_project_id(self, project_id: int, data: Dict[str, Any]) -> Optional[ProjectSettings]:
        """Update project settings by project ID"""
        try:
            # Get existing settings
            existing = self.get_by_project_id(project_id)
            if not existing:
                # Create new settings if they don't exist
                data['project_id'] = project_id
                return self.create(data)
            
            return self.update(existing.id, data)
            
        except Exception as e:
            logger.error(f"Failed to update project settings for project {project_id}: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError)):
                raise
            raise DatabaseError(f"Project settings update failed: {str(e)}")
    
    def delete(self, settings_id: int) -> bool:
        """Delete project settings"""
        try:
            query = "DELETE FROM project_settings WHERE id = ?"
            rows_affected = self.db_manager.execute_command(query, (settings_id,))
            
            if rows_affected > 0:
                logger.info(f"Deleted project settings {settings_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete project settings {settings_id}: {str(e)}")
            raise DatabaseError(f"Project settings deletion failed: {str(e)}")
    
    def delete_by_project_id(self, project_id: int) -> bool:
        """Delete project settings by project ID"""
        try:
            query = "DELETE FROM project_settings WHERE project_id = ?"
            rows_affected = self.db_manager.execute_command(query, (project_id,))
            
            if rows_affected > 0:
                logger.info(f"Deleted project settings for project {project_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete project settings for project {project_id}: {str(e)}")
            raise DatabaseError(f"Project settings deletion failed: {str(e)}")
    
    def get_planning_statement(self, project_id: int) -> Optional[str]:
        """Get planning statement for a project"""
        try:
            settings = self.get_by_project_id(project_id)
            return settings.planning_statement if settings else None
            
        except Exception as e:
            logger.error(f"Failed to get planning statement for project {project_id}: {str(e)}")
            raise DatabaseError(f"Failed to get planning statement: {str(e)}")
    
    def get_setup_commands(self, project_id: int) -> Optional[str]:
        """Get setup commands for a project"""
        try:
            settings = self.get_by_project_id(project_id)
            return settings.setup_commands if settings else None
            
        except Exception as e:
            logger.error(f"Failed to get setup commands for project {project_id}: {str(e)}")
            raise DatabaseError(f"Failed to get setup commands: {str(e)}")
    
    def get_repository_rules(self, project_id: int) -> Optional[str]:
        """Get repository rules for a project"""
        try:
            settings = self.get_by_project_id(project_id)
            return settings.repository_rules if settings else None
            
        except Exception as e:
            logger.error(f"Failed to get repository rules for project {project_id}: {str(e)}")
            raise DatabaseError(f"Failed to get repository rules: {str(e)}")
    
    def update_planning_statement(self, project_id: int, planning_statement: str) -> bool:
        """Update planning statement for a project"""
        try:
            existing = self.get_by_project_id(project_id)
            if not existing:
                # Create new settings with planning statement
                data = {
                    'project_id': project_id,
                    'planning_statement': planning_statement
                }
                self.create(data)
                return True
            
            # Update existing settings
            data = {'planning_statement': planning_statement}
            updated = self.update(existing.id, data)
            return updated is not None
            
        except Exception as e:
            logger.error(f"Failed to update planning statement for project {project_id}: {str(e)}")
            raise DatabaseError(f"Failed to update planning statement: {str(e)}")

