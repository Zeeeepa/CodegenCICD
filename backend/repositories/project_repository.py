"""
Project Repository - CRUD operations for projects table
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import sqlite3
import logging

from ..models.project import Project
from ..database import get_database_connection

logger = logging.getLogger(__name__)


class ProjectRepository:
    """Repository for Project entity with CRUD operations"""
    
    def __init__(self):
        self.table_name = "projects"
    
    def create(self, data: Dict[str, Any]) -> Project:
        """Create a new project"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                # Prepare data with timestamps
                now = datetime.utcnow().isoformat()
                data['created_at'] = now
                data['updated_at'] = now
                
                # Insert project
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
                
                cursor.execute(query, list(data.values()))
                project_id = cursor.lastrowid
                
                conn.commit()
                
                # Return created project
                return self.get_by_id(project_id)
                
        except sqlite3.Error as e:
            logger.error(f"Database error creating project: {e}")
            raise Exception(f"Failed to create project: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            raise
    
    def get_by_id(self, project_id: int) -> Optional[Project]:
        """Get project by ID"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                query = f"SELECT * FROM {self.table_name} WHERE id = ?"
                cursor.execute(query, (project_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_project(row, cursor.description)
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Database error getting project {project_id}: {e}")
            raise Exception(f"Failed to get project: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting project {project_id}: {e}")
            raise
    
    def get_by_github_repo(self, owner: str, repo: str) -> Optional[Project]:
        """Get project by GitHub repository"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                query = f"SELECT * FROM {self.table_name} WHERE github_owner = ? AND github_repo = ?"
                cursor.execute(query, (owner, repo))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_project(row, cursor.description)
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Database error getting project {owner}/{repo}: {e}")
            raise Exception(f"Failed to get project: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting project {owner}/{repo}: {e}")
            raise
    
    def list_active_projects(self) -> List[Project]:
        """List all active projects"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                query = f"SELECT * FROM {self.table_name} WHERE status = 'active' ORDER BY created_at DESC"
                cursor.execute(query)
                rows = cursor.fetchall()
                
                return [self._row_to_project(row, cursor.description) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"Database error listing active projects: {e}")
            raise Exception(f"Failed to list projects: {str(e)}")
        except Exception as e:
            logger.error(f"Error listing active projects: {e}")
            raise
    
    def list_all(self) -> List[Project]:
        """List all projects"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                query = f"SELECT * FROM {self.table_name} ORDER BY created_at DESC"
                cursor.execute(query)
                rows = cursor.fetchall()
                
                return [self._row_to_project(row, cursor.description) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"Database error listing all projects: {e}")
            raise Exception(f"Failed to list projects: {str(e)}")
        except Exception as e:
            logger.error(f"Error listing all projects: {e}")
            raise
    
    def update(self, project_id: int, data: Dict[str, Any]) -> Optional[Project]:
        """Update project"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                # Add updated timestamp
                data['updated_at'] = datetime.utcnow().isoformat()
                
                # Build update query
                set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
                query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?"
                
                values = list(data.values()) + [project_id]
                cursor.execute(query, values)
                
                if cursor.rowcount == 0:
                    return None
                
                conn.commit()
                
                # Return updated project
                return self.get_by_id(project_id)
                
        except sqlite3.Error as e:
            logger.error(f"Database error updating project {project_id}: {e}")
            raise Exception(f"Failed to update project: {str(e)}")
        except Exception as e:
            logger.error(f"Error updating project {project_id}: {e}")
            raise
    
    def update_webhook_url(self, project_id: int, webhook_url: str) -> bool:
        """Update project webhook URL"""
        try:
            result = self.update(project_id, {'webhook_url': webhook_url})
            return result is not None
        except Exception as e:
            logger.error(f"Error updating webhook URL for project {project_id}: {e}")
            raise
    
    def delete(self, project_id: int) -> bool:
        """Delete project"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                query = f"DELETE FROM {self.table_name} WHERE id = ?"
                cursor.execute(query, (project_id,))
                
                deleted = cursor.rowcount > 0
                conn.commit()
                
                return deleted
                
        except sqlite3.Error as e:
            logger.error(f"Database error deleting project {project_id}: {e}")
            raise Exception(f"Failed to delete project: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {e}")
            raise
    
    def _row_to_project(self, row: tuple, description: List) -> Project:
        """Convert database row to Project model"""
        try:
            # Create dict from row data
            columns = [col[0] for col in description]
            data = dict(zip(columns, row))
            
            # Add mock stats for now
            data['stats'] = {
                'totalRuns': 0,
                'successRate': 0,
                'lastRunAt': None,
                'averageRunTime': None,
                'failureCount': 0
            }
            
            return Project(**data)
            
        except Exception as e:
            logger.error(f"Error converting row to project: {e}")
            raise Exception(f"Failed to convert database row: {str(e)}")

