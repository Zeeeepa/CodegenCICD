"""
Base repository class for database operations
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Dict, Any
from contextlib import asynccontextmanager
import structlog
from datetime import datetime
from sqlalchemy import text

from backend.database import get_db_session

logger = structlog.get_logger(__name__)

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):
    """Base repository class with common CRUD operations"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
    
    @abstractmethod
    def _row_to_model(self, row: Dict[str, Any]) -> T:
        """Convert database row to model instance"""
        pass
    
    @abstractmethod
    def _model_to_dict(self, model: T) -> Dict[str, Any]:
        """Convert model instance to dictionary for database"""
        pass
    
    async def create(self, data: Dict[str, Any]) -> Optional[T]:
        """Create a new record"""
        try:
            # Add timestamps
            now = datetime.utcnow()
            data['created_at'] = now
            data['updated_at'] = now
            
            # Build INSERT query
            columns = list(data.keys())
            placeholders = ', '.join([f':{key}' for key in columns])
            
            query = f"""
                INSERT INTO {self.table_name} ({', '.join(columns)})
                VALUES ({placeholders})
                RETURNING id
            """
            
            async with get_db_session() as session:
                result = await session.execute(text(query), data)
                record_id = result.scalar()
                await session.commit()
                
                # Return the created record
                return await self.get_by_id(record_id)
                
        except Exception as e:
            logger.error(f"Error creating record in {self.table_name}", error=str(e))
            return None
    
    async def get_by_id(self, record_id: int) -> Optional[T]:
        """Get record by ID"""
        try:
            query = f"SELECT * FROM {self.table_name} WHERE id = :record_id"
            
            async with get_db_session() as session:
                result = await session.execute(text(query), {"record_id": record_id})
                row = result.fetchone()
                
                if row:
                    # Convert row to dict
                    row_dict = dict(row._mapping)
                    return self._row_to_model(row_dict)
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting record from {self.table_name}", record_id=record_id, error=str(e))
            return None
    
    async def update(self, record_id: int, data: Dict[str, Any]) -> Optional[T]:
        """Update record by ID"""
        try:
            # Add updated timestamp
            data['updated_at'] = datetime.utcnow()
            data['id'] = record_id
            
            # Build UPDATE query
            set_clauses = [f"{key} = :{key}" for key in data.keys() if key != 'id']
            
            query = f"""
                UPDATE {self.table_name}
                SET {', '.join(set_clauses)}
                WHERE id = :id
            """
            
            async with get_db_session() as session:
                result = await session.execute(text(query), data)
                await session.commit()
                
                if result.rowcount > 0:
                    return await self.get_by_id(record_id)
                
                return None
                
        except Exception as e:
            logger.error(f"Error updating record in {self.table_name}", record_id=record_id, error=str(e))
            return None
    
    async def delete(self, record_id: int) -> bool:
        """Delete record by ID"""
        try:
            query = f"DELETE FROM {self.table_name} WHERE id = :record_id"
            
            async with get_db_session() as session:
                result = await session.execute(text(query), {"record_id": record_id})
                await session.commit()
                
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error deleting record from {self.table_name}", record_id=record_id, error=str(e))
            return False
    
    async def list_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """List all records with optional pagination"""
        try:
            query = f"SELECT * FROM {self.table_name} ORDER BY created_at DESC"
            params = {}
            
            if limit:
                query += f" LIMIT :limit OFFSET :offset"
                params = {"limit": limit, "offset": offset}
            
            async with get_db_session() as session:
                result = await session.execute(text(query), params)
                rows = result.fetchall()
                
                # Convert rows to models
                results = []
                
                for row in rows:
                    row_dict = dict(row._mapping)
                    model = self._row_to_model(row_dict)
                    if model:
                        results.append(model)
                
                return results
                
        except Exception as e:
            logger.error(f"Error listing records from {self.table_name}", error=str(e))
            return []
    
    async def count(self) -> int:
        """Count total records"""
        try:
            query = f"SELECT COUNT(*) FROM {self.table_name}"
            
            async with get_db_session() as session:
                result = await session.execute(text(query))
                row = result.fetchone()
                return row[0] if row else 0
                
        except Exception as e:
            logger.error(f"Error counting records in {self.table_name}", error=str(e))
            return 0
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions"""
        async with get_db_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
