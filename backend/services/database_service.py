"""
Database service layer for coordinating repository operations
"""
from typing import Dict, Any, List, Optional
import structlog
from datetime import datetime

from backend.repositories.project_repository import ProjectRepository
from backend.models.project import Project
from backend.database import get_db_session
from sqlalchemy import text

logger = structlog.get_logger(__name__)

class DatabaseService:
    """Service layer for coordinating database operations"""
    
    def __init__(self):
        self.project_repo = ProjectRepository()
    
    async def create_project_with_settings(
        self, 
        project_data: Dict[str, Any], 
        settings_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Project]:
        """Create a project with optional settings in a transaction"""
        try:
            async with self.project_repo.transaction() as session:
                # Create the project
                project = await self.project_repo.create(project_data)
                
                if not project:
                    logger.error("Failed to create project")
                    return None
                
                # Create settings if provided
                if settings_data and project.id:
                    settings_data['project_id'] = project.id
                    settings_data['created_at'] = datetime.utcnow()
                    settings_data['updated_at'] = datetime.utcnow()
                    
                    # Insert project settings
                    columns = list(settings_data.keys())
                    placeholders = ', '.join([f':{key}' for key in columns])
                    
                    query = f"""
                        INSERT INTO project_settings ({', '.join(columns)})
                        VALUES ({placeholders})
                    """
                    
                    await session.execute(text(query), settings_data)
                
                logger.info("Successfully created project with settings", project_id=project.id)
                return project
                
        except Exception as e:
            logger.error("Error creating project with settings", error=str(e))
            return None
    
    async def get_project_full_config(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get project with all related configuration data"""
        try:
            # Get the project
            project = await self.project_repo.get_by_id(project_id)
            if not project:
                return None
            
            result = {
                'project': project.dict(),
                'settings': None,
                'secrets': [],
                'agent_runs': []
            }
            
            async with get_db_session() as session:
                # Get project settings
                settings_query = "SELECT * FROM project_settings WHERE project_id = :project_id"
                result_set = await session.execute(text(settings_query), {"project_id": project_id})
                settings_row = result_set.fetchone()
                
                if settings_row:
                    result['settings'] = dict(settings_row._mapping)
                
                # Get project secrets (without decrypted values for security)
                secrets_query = "SELECT id, project_id, key_name, created_at FROM project_secrets WHERE project_id = :project_id"
                result_set = await session.execute(text(secrets_query), {"project_id": project_id})
                secrets_rows = result_set.fetchall()
                
                if secrets_rows:
                    result['secrets'] = [dict(row._mapping) for row in secrets_rows]
                
                # Get recent agent runs
                agent_runs_query = """
                    SELECT id, project_id, status, prompt, created_at, updated_at 
                    FROM agent_runs 
                    WHERE project_id = :project_id 
                    ORDER BY created_at DESC 
                    LIMIT 10
                """
                result_set = await session.execute(text(agent_runs_query), {"project_id": project_id})
                agent_runs_rows = result_set.fetchall()
                
                if agent_runs_rows:
                    result['agent_runs'] = [dict(row._mapping) for row in agent_runs_rows]
            
            return result
            
        except Exception as e:
            logger.error("Error getting project full config", project_id=project_id, error=str(e))
            return None
    
    async def update_project_secrets(
        self, 
        project_id: int, 
        secrets: List[Dict[str, str]]
    ) -> bool:
        """Update project secrets (encrypted)"""
        try:
            async with get_db_session() as session:
                # First, delete existing secrets
                delete_query = "DELETE FROM project_secrets WHERE project_id = :project_id"
                await session.execute(text(delete_query), {"project_id": project_id})
                
                # Insert new secrets
                for secret in secrets:
                    # TODO: Implement encryption here
                    encrypted_value = secret['value']  # Placeholder - should be encrypted
                    
                    insert_query = """
                        INSERT INTO project_secrets (project_id, key_name, encrypted_value, created_at)
                        VALUES (:project_id, :key_name, :encrypted_value, :created_at)
                    """
                    
                    await session.execute(text(insert_query), {
                        "project_id": project_id,
                        "key_name": secret['key_name'],
                        "encrypted_value": encrypted_value,
                        "created_at": datetime.utcnow()
                    })
                
                await session.commit()
                logger.info("Successfully updated project secrets", project_id=project_id, count=len(secrets))
                return True
                
        except Exception as e:
            logger.error("Error updating project secrets", project_id=project_id, error=str(e))
            return False
    
    async def get_project_stats(self, project_id: int) -> Dict[str, Any]:
        """Get project statistics"""
        try:
            stats = {
                'total_runs': 0,
                'successful_runs': 0,
                'failed_runs': 0,
                'pending_runs': 0,
                'success_rate': 0.0,
                'last_run_at': None
            }
            
            async with get_db_session() as session:
                # Get run statistics
                stats_query = """
                    SELECT 
                        COUNT(*) as total_runs,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_runs,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs,
                        SUM(CASE WHEN status IN ('pending', 'running') THEN 1 ELSE 0 END) as pending_runs,
                        MAX(created_at) as last_run_at
                    FROM agent_runs 
                    WHERE project_id = :project_id
                """
                
                result = await session.execute(text(stats_query), {"project_id": project_id})
                row = result.fetchone()
                
                if row:
                    stats['total_runs'] = row[0] or 0
                    stats['successful_runs'] = row[1] or 0
                    stats['failed_runs'] = row[2] or 0
                    stats['pending_runs'] = row[3] or 0
                    stats['last_run_at'] = row[4]
                    
                    # Calculate success rate
                    if stats['total_runs'] > 0:
                        stats['success_rate'] = (stats['successful_runs'] / stats['total_runs']) * 100
            
            return stats
            
        except Exception as e:
            logger.error("Error getting project stats", project_id=project_id, error=str(e))
            return {
                'total_runs': 0,
                'successful_runs': 0,
                'failed_runs': 0,
                'pending_runs': 0,
                'success_rate': 0.0,
                'last_run_at': None
            }
    
    async def search_projects_with_stats(self, search_term: str = "") -> List[Dict[str, Any]]:
        """Search projects and include basic statistics"""
        try:
            if search_term:
                projects = await self.project_repo.search_projects(search_term)
            else:
                projects = await self.project_repo.list_active_projects()
            
            results = []
            for project in projects:
                project_data = project.dict()
                
                # Add basic stats
                if project.id:
                    stats = await self.get_project_stats(project.id)
                    project_data['stats'] = stats
                
                results.append(project_data)
            
            return results
            
        except Exception as e:
            logger.error("Error searching projects with stats", search_term=search_term, error=str(e))
            return []
