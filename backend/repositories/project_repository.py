"""
Project repository implementation using foundation database layer
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from database.base import BaseRepository
from database.connection_manager import DatabaseManager
from models import Project
from errors.exceptions import DatabaseError, ValidationError

logger = logging.getLogger(__name__)


class ProjectRepository(BaseRepository[Project]):
    """Repository for project CRUD operations"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(Project, "projects", db_manager)
    
    def create(self, data: Dict[str, Any]) -> Project:
        """Create a new project with validation"""
        try:
            # Validate required fields
            if not data.get('name') or not data.get('github_owner') or not data.get('github_repo'):
                raise ValidationError("Missing required fields: name, github_owner, github_repo")
            
            # Check for duplicate github repo
            existing = self.get_by_github_repo(data['github_owner'], data['github_repo'])
            if existing:
                raise ValidationError(f"Project already exists for {data['github_owner']}/{data['github_repo']}")
            
            # Set timestamps
            now = datetime.utcnow()
            data['created_at'] = now
            data['updated_at'] = now
            
            # Execute insert
            query = """
                INSERT INTO projects (name, github_owner, github_repo, status, webhook_url, 
                                    auto_merge_enabled, auto_confirm_plans, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                data['name'],
                data['github_owner'],
                data['github_repo'],
                data.get('status', 'active'),
                data.get('webhook_url'),
                data.get('auto_merge_enabled', False),
                data.get('auto_confirm_plans', False),
                data['created_at'],
                data['updated_at']
            )
            
            project_id = self.db_manager.execute_command(query, params)
            
            # Return created project
            created_project = self.get_by_id(project_id)
            if not created_project:
                raise DatabaseError("Failed to retrieve created project")
            
            logger.info(f"Created project {project_id}: {data['github_owner']}/{data['github_repo']}")
            return created_project
            
        except Exception as e:
            logger.error(f"Failed to create project: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError)):
                raise
            raise DatabaseError(f"Project creation failed: {str(e)}")
    
    def get_by_id(self, project_id: int) -> Optional[Project]:
        """Get project by ID"""
        try:
            query = "SELECT * FROM projects WHERE id = ?"
            results = self.db_manager.execute_query(query, (project_id,))
            
            if not results:
                return None
            
            return Project(**results[0])
            
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {str(e)}")
            raise DatabaseError(f"Failed to retrieve project: {str(e)}")
    
    def get_by_github_repo(self, owner: str, repo: str) -> Optional[Project]:
        """Get project by GitHub owner and repository name"""
        try:
            query = "SELECT * FROM projects WHERE github_owner = ? AND github_repo = ?"
            results = self.db_manager.execute_query(query, (owner, repo))
            
            if not results:
                return None
            
            return Project(**results[0])
            
        except Exception as e:
            logger.error(f"Failed to get project {owner}/{repo}: {str(e)}")
            raise DatabaseError(f"Failed to retrieve project: {str(e)}")
    
    def list_active_projects(self) -> List[Project]:
        """Get all active projects"""
        try:
            query = "SELECT * FROM projects WHERE status = 'active' ORDER BY updated_at DESC"
            results = self.db_manager.execute_query(query)
            
            return [Project(**row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to list active projects: {str(e)}")
            raise DatabaseError(f"Failed to list projects: {str(e)}")
    
    def list_all_projects(self, limit: int = 100, offset: int = 0) -> List[Project]:
        """Get all projects with pagination"""
        try:
            query = "SELECT * FROM projects ORDER BY updated_at DESC LIMIT ? OFFSET ?"
            results = self.db_manager.execute_query(query, (limit, offset))
            
            return [Project(**row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to list projects: {str(e)}")
            raise DatabaseError(f"Failed to list projects: {str(e)}")
    
    def update(self, project_id: int, data: Dict[str, Any]) -> Optional[Project]:
        """Update project with validation"""
        try:
            # Get existing project
            existing = self.get_by_id(project_id)
            if not existing:
                return None
            
            # Validate github repo uniqueness if changed
            if 'github_owner' in data or 'github_repo' in data:
                new_owner = data.get('github_owner', existing.github_owner)
                new_repo = data.get('github_repo', existing.github_repo)
                
                if new_owner != existing.github_owner or new_repo != existing.github_repo:
                    existing_project = self.get_by_github_repo(new_owner, new_repo)
                    if existing_project and existing_project.id != project_id:
                        raise ValidationError(f"Project already exists for {new_owner}/{new_repo}")
            
            # Set update timestamp
            data['updated_at'] = datetime.utcnow()
            
            # Build update query dynamically
            update_fields = []
            params = []
            
            for field, value in data.items():
                if field in ['name', 'github_owner', 'github_repo', 'status', 'webhook_url', 
                           'auto_merge_enabled', 'auto_confirm_plans', 'updated_at']:
                    update_fields.append(f"{field} = ?")
                    params.append(value)
            
            if not update_fields:
                return existing  # No valid fields to update
            
            params.append(project_id)
            query = f"UPDATE projects SET {', '.join(update_fields)} WHERE id = ?"
            
            rows_affected = self.db_manager.execute_command(query, tuple(params))
            
            if rows_affected == 0:
                return None
            
            # Return updated project
            updated_project = self.get_by_id(project_id)
            logger.info(f"Updated project {project_id}")
            return updated_project
            
        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError)):
                raise
            raise DatabaseError(f"Project update failed: {str(e)}")
    
    def update_webhook_url(self, project_id: int, webhook_url: str) -> bool:
        """Update webhook URL for a project"""
        try:
            query = "UPDATE projects SET webhook_url = ?, updated_at = ? WHERE id = ?"
            params = (webhook_url, datetime.utcnow(), project_id)
            
            rows_affected = self.db_manager.execute_command(query, params)
            
            if rows_affected > 0:
                logger.info(f"Updated webhook URL for project {project_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update webhook URL for project {project_id}: {str(e)}")
            raise DatabaseError(f"Webhook URL update failed: {str(e)}")
    
    def delete(self, project_id: int) -> bool:
        """Delete a project (soft delete by setting status to 'deleted')"""
        try:
            query = "UPDATE projects SET status = 'deleted', updated_at = ? WHERE id = ?"
            params = (datetime.utcnow(), project_id)
            
            rows_affected = self.db_manager.execute_command(query, params)
            
            if rows_affected > 0:
                logger.info(f"Deleted project {project_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {str(e)}")
            raise DatabaseError(f"Project deletion failed: {str(e)}")
    
    def get_project_count(self) -> int:
        """Get total count of active projects"""
        try:
            query = "SELECT COUNT(*) as count FROM projects WHERE status = 'active'"
            results = self.db_manager.execute_query(query)
            
            return results[0]['count'] if results else 0
            
        except Exception as e:
            logger.error(f"Failed to get project count: {str(e)}")
            raise DatabaseError(f"Failed to get project count: {str(e)}")
    
    def search_projects(self, search_term: str, limit: int = 50) -> List[Project]:
        """Search projects by name or GitHub repository"""
        try:
            search_pattern = f"%{search_term}%"
            query = """
                SELECT * FROM projects 
                WHERE status = 'active' 
                AND (name LIKE ? OR github_owner LIKE ? OR github_repo LIKE ?)
                ORDER BY updated_at DESC 
                LIMIT ?
            """
            params = (search_pattern, search_pattern, search_pattern, limit)
            results = self.db_manager.execute_query(query, params)
            
            return [Project(**row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to search projects: {str(e)}")
            raise DatabaseError(f"Project search failed: {str(e)}")

