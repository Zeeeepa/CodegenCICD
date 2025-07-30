"""
Project Settings Repository - CRUD operations for project_settings table
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import sqlite3
import logging

from ..models.project import ProjectSettings
from ..database import get_database_connection

logger = logging.getLogger(__name__)


class ProjectSettingsRepository:
    """Repository for ProjectSettings entity with CRUD operations"""
    
    def __init__(self):
        self.table_name = "project_settings"
    
    def create(self, data: Dict[str, Any]) -> ProjectSettings:
        """Create new project settings"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                # Prepare data with timestamps
                now = datetime.utcnow().isoformat()
                data['created_at'] = now
                data['updated_at'] = now
                
                # Insert settings
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
                
                cursor.execute(query, list(data.values()))
                settings_id = cursor.lastrowid
                
                conn.commit()
                
                # Return created settings
                return self.get_by_id(settings_id)
                
        except sqlite3.Error as e:
            logger.error(f"Database error creating project settings: {e}")
            raise Exception(f"Failed to create project settings: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating project settings: {e}")
            raise
    
    def get_by_id(self, settings_id: int) -> Optional[ProjectSettings]:
        """Get project settings by ID"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                query = f"SELECT * FROM {self.table_name} WHERE id = ?"
                cursor.execute(query, (settings_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_settings(row, cursor.description)
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Database error getting project settings {settings_id}: {e}")
            raise Exception(f"Failed to get project settings: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting project settings {settings_id}: {e}")
            raise
    
    def get_by_project_id(self, project_id: int) -> Optional[ProjectSettings]:
        """Get project settings by project ID"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                query = f"SELECT * FROM {self.table_name} WHERE project_id = ?"
                cursor.execute(query, (project_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_settings(row, cursor.description)
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Database error getting settings for project {project_id}: {e}")
            raise Exception(f"Failed to get project settings: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting settings for project {project_id}: {e}")
            raise
    
    def update(self, settings_id: int, data: Dict[str, Any]) -> Optional[ProjectSettings]:
        """Update project settings"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                # Add updated timestamp
                data['updated_at'] = datetime.utcnow().isoformat()
                
                # Build update query
                set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
                query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?"
                
                values = list(data.values()) + [settings_id]
                cursor.execute(query, values)
                
                if cursor.rowcount == 0:
                    return None
                
                conn.commit()
                
                # Return updated settings
                return self.get_by_id(settings_id)
                
        except sqlite3.Error as e:
            logger.error(f"Database error updating project settings {settings_id}: {e}")
            raise Exception(f"Failed to update project settings: {str(e)}")
        except Exception as e:
            logger.error(f"Error updating project settings {settings_id}: {e}")
            raise
    
    def update_by_project_id(self, project_id: int, data: Dict[str, Any]) -> Optional[ProjectSettings]:
        """Update project settings by project ID"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                # Add updated timestamp
                data['updated_at'] = datetime.utcnow().isoformat()
                
                # Build update query
                set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
                query = f"UPDATE {self.table_name} SET {set_clause} WHERE project_id = ?"
                
                values = list(data.values()) + [project_id]
                cursor.execute(query, values)
                
                if cursor.rowcount == 0:
                    return None
                
                conn.commit()
                
                # Return updated settings
                return self.get_by_project_id(project_id)
                
        except sqlite3.Error as e:
            logger.error(f"Database error updating settings for project {project_id}: {e}")
            raise Exception(f"Failed to update project settings: {str(e)}")
        except Exception as e:
            logger.error(f"Error updating settings for project {project_id}: {e}")
            raise
    
    def delete(self, settings_id: int) -> bool:
        """Delete project settings"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                query = f"DELETE FROM {self.table_name} WHERE id = ?"
                cursor.execute(query, (settings_id,))
                
                deleted = cursor.rowcount > 0
                conn.commit()
                
                return deleted
                
        except sqlite3.Error as e:
            logger.error(f"Database error deleting project settings {settings_id}: {e}")
            raise Exception(f"Failed to delete project settings: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting project settings {settings_id}: {e}")
            raise
    
    def delete_by_project_id(self, project_id: int) -> bool:
        """Delete project settings by project ID"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                query = f"DELETE FROM {self.table_name} WHERE project_id = ?"
                cursor.execute(query, (project_id,))
                
                deleted = cursor.rowcount > 0
                conn.commit()
                
                return deleted
                
        except sqlite3.Error as e:
            logger.error(f"Database error deleting settings for project {project_id}: {e}")
            raise Exception(f"Failed to delete project settings: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting settings for project {project_id}: {e}")
            raise
    
    def _row_to_settings(self, row: tuple, description: List) -> ProjectSettings:
        """Convert database row to ProjectSettings model"""
        try:
            # Create dict from row data
            columns = [col[0] for col in description]
            data = dict(zip(columns, row))
            
            return ProjectSettings(**data)
            
        except Exception as e:
            logger.error(f"Error converting row to project settings: {e}")
            raise Exception(f"Failed to convert database row: {str(e)}")

