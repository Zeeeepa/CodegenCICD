"""
Project repository for database operations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog

from .base import BaseRepository
from backend.models.project import Project
from backend.database import get_db_session
from sqlalchemy import text

logger = structlog.get_logger(__name__)

class ProjectRepository(BaseRepository[Project]):
    """Repository for Project model operations"""
    
    def __init__(self):
        super().__init__("projects")
    
    def _row_to_model(self, row: Dict[str, Any]) -> Optional[Project]:
        """Convert database row to Project model"""
        try:
            return Project(
                id=row.get('id'),
                name=row.get('name'),
                github_owner=row.get('github_owner'),
                github_repo=row.get('github_repo'),
                status=row.get('status', 'active'),
                webhook_url=row.get('webhook_url'),
                auto_merge_enabled=bool(row.get('auto_merge_enabled', False)),
                auto_confirm_plans=bool(row.get('auto_confirm_plans', False)),
                created_at=row.get('created_at'),
                updated_at=row.get('updated_at')
            )
        except Exception as e:
            logger.error("Error converting row to Project model", error=str(e), row=row)
            return None
    
    def _model_to_dict(self, model: Project) -> Dict[str, Any]:
        """Convert Project model to dictionary"""
        return {
            'name': model.name,
            'github_owner': model.github_owner,
            'github_repo': model.github_repo,
            'status': model.status,
            'webhook_url': model.webhook_url,
            'auto_merge_enabled': model.auto_merge_enabled,
            'auto_confirm_plans': model.auto_confirm_plans
        }
    
    async def get_by_github_repo(self, owner: str, repo: str) -> Optional[Project]:
        """Get project by GitHub owner and repository name"""
        try:
            query = """
                SELECT * FROM projects 
                WHERE github_owner = :owner AND github_repo = :repo
            """
            
            async with get_db_session() as session:
                result = await session.execute(text(query), {"owner": owner, "repo": repo})
                row = result.fetchone()
                
                if row:
                    row_dict = dict(row._mapping)
                    return self._row_to_model(row_dict)
                
                return None
                
        except Exception as e:
            logger.error("Error getting project by GitHub repo", owner=owner, repo=repo, error=str(e))
            return None
    
    async def list_active_projects(self) -> List[Project]:
        """List all active projects"""
        try:
            query = """
                SELECT * FROM projects 
                WHERE status = 'active' 
                ORDER BY created_at DESC
            """
            
            async with get_db_session() as session:
                result = await session.execute(text(query))
                rows = result.fetchall()
                
                results = []
                
                for row in rows:
                    row_dict = dict(row._mapping)
                    model = self._row_to_model(row_dict)
                    if model:
                        results.append(model)
                
                return results
                
        except Exception as e:
            logger.error("Error listing active projects", error=str(e))
            return []
    
    async def update_webhook_url(self, project_id: int, webhook_url: str) -> bool:
        """Update webhook URL for a project"""
        try:
            query = """
                UPDATE projects 
                SET webhook_url = :webhook_url, updated_at = :updated_at
                WHERE id = :project_id
            """
            
            async with get_db_session() as session:
                result = await session.execute(text(query), {
                    "webhook_url": webhook_url,
                    "updated_at": datetime.utcnow(),
                    "project_id": project_id
                })
                await session.commit()
                
                return result.rowcount > 0
                
        except Exception as e:
            logger.error("Error updating webhook URL", project_id=project_id, error=str(e))
            return False
    
    async def update_status(self, project_id: int, status: str) -> bool:
        """Update project status"""
        try:
            query = """
                UPDATE projects 
                SET status = :status, updated_at = :updated_at
                WHERE id = :project_id
            """
            
            async with get_db_session() as session:
                result = await session.execute(text(query), {
                    "status": status,
                    "updated_at": datetime.utcnow(),
                    "project_id": project_id
                })
                await session.commit()
                
                return result.rowcount > 0
                
        except Exception as e:
            logger.error("Error updating project status", project_id=project_id, status=status, error=str(e))
            return False
    
    async def search_projects(self, search_term: str) -> List[Project]:
        """Search projects by name, owner, or repo"""
        try:
            query = """
                SELECT * FROM projects 
                WHERE name LIKE :search_pattern OR github_owner LIKE :search_pattern OR github_repo LIKE :search_pattern
                ORDER BY created_at DESC
            """
            
            search_pattern = f"%{search_term}%"
            
            async with get_db_session() as session:
                result = await session.execute(text(query), {"search_pattern": search_pattern})
                rows = result.fetchall()
                
                results = []
                
                for row in rows:
                    row_dict = dict(row._mapping)
                    model = self._row_to_model(row_dict)
                    if model:
                        results.append(model)
                
                return results
                
        except Exception as e:
            logger.error("Error searching projects", search_term=search_term, error=str(e))
            return []
