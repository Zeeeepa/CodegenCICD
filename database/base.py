"""
Database Base Classes and Utilities

This module provides base classes and utilities for database operations
including repository patterns, query builders, and common database operations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from datetime import datetime

from models import BaseDBModel
from database.connection_manager import get_database_manager, DatabaseManager

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseDBModel)


class BaseRepository(Generic[T], ABC):
    """Base repository class for database operations"""
    
    def __init__(self, model_class: Type[T], table_name: str, db_manager: Optional[DatabaseManager] = None):
        self.model_class = model_class
        self.table_name = table_name
        self.db_manager = db_manager or get_database_manager()
        
    def create(self, data: Dict[str, Any]) -> T:
        """Create a new record"""
        # Remove None values and id if present
        clean_data = {k: v for k, v in data.items() if v is not None and k != 'id'}
        
        # Build INSERT query
        columns = list(clean_data.keys())
        placeholders = ', '.join(['?' for _ in columns])
        values = list(clean_data.values())
        
        query = f"""
            INSERT INTO {self.table_name} ({', '.join(columns)})
            VALUES ({placeholders})
        """
        
        try:
            with self.db_manager.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                record_id = cursor.lastrowid
                
            # Fetch and return the created record
            return self.get_by_id(record_id)
            
        except Exception as e:
            logger.error(f"Error creating {self.model_class.__name__}: {e}")
            raise
    
    def get_by_id(self, record_id: int) -> Optional[T]:
        """Get a record by ID"""
        query = f"SELECT * FROM {self.table_name} WHERE id = ?"
        
        try:
            results = self.db_manager.execute_query(query, (record_id,))
            
            if results:
                return self.model_class(**results[0])
            return None
            
        except Exception as e:
            logger.error(f"Error getting {self.model_class.__name__} by ID {record_id}: {e}")
            raise
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all records with pagination"""
        query = f"""
            SELECT * FROM {self.table_name}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        
        try:
            results = self.db_manager.execute_query(query, (limit, offset))
            return [self.model_class(**row) for row in results]
            
        except Exception as e:
            logger.error(f"Error getting all {self.model_class.__name__}: {e}")
            raise
    
    def update(self, record_id: int, data: Dict[str, Any]) -> Optional[T]:
        """Update a record by ID"""
        # Remove None values and id
        clean_data = {k: v for k, v in data.items() if v is not None and k != 'id'}
        
        if not clean_data:
            return self.get_by_id(record_id)
        
        # Build UPDATE query
        set_clauses = [f"{k} = ?" for k in clean_data.keys()]
        values = list(clean_data.values()) + [record_id]
        
        query = f"""
            UPDATE {self.table_name}
            SET {', '.join(set_clauses)}
            WHERE id = ?
        """
        
        try:
            rows_affected = self.db_manager.execute_command(query, values)
            
            if rows_affected > 0:
                return self.get_by_id(record_id)
            return None
            
        except Exception as e:
            logger.error(f"Error updating {self.model_class.__name__} {record_id}: {e}")
            raise
    
    def delete(self, record_id: int) -> bool:
        """Delete a record by ID"""
        query = f"DELETE FROM {self.table_name} WHERE id = ?"
        
        try:
            rows_affected = self.db_manager.execute_command(query, (record_id,))
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"Error deleting {self.model_class.__name__} {record_id}: {e}")
            raise
    
    def count(self, where_clause: str = "", params: Optional[tuple] = None) -> int:
        """Count records with optional WHERE clause"""
        query = f"SELECT COUNT(*) as count FROM {self.table_name}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        try:
            results = self.db_manager.execute_query(query, params)
            return results[0]["count"] if results else 0
            
        except Exception as e:
            logger.error(f"Error counting {self.model_class.__name__}: {e}")
            raise
    
    def find_by(self, **kwargs) -> List[T]:
        """Find records by field values"""
        if not kwargs:
            return self.get_all()
        
        # Build WHERE clause
        conditions = []
        values = []
        
        for key, value in kwargs.items():
            if value is not None:
                conditions.append(f"{key} = ?")
                values.append(value)
        
        if not conditions:
            return self.get_all()
        
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE {' AND '.join(conditions)}
            ORDER BY created_at DESC
        """
        
        try:
            results = self.db_manager.execute_query(query, tuple(values))
            return [self.model_class(**row) for row in results]
            
        except Exception as e:
            logger.error(f"Error finding {self.model_class.__name__}: {e}")
            raise
    
    def find_one_by(self, **kwargs) -> Optional[T]:
        """Find one record by field values"""
        results = self.find_by(**kwargs)
        return results[0] if results else None
    
    def exists(self, record_id: int) -> bool:
        """Check if a record exists by ID"""
        query = f"SELECT 1 FROM {self.table_name} WHERE id = ? LIMIT 1"
        
        try:
            results = self.db_manager.execute_query(query, (record_id,))
            return len(results) > 0
            
        except Exception as e:
            logger.error(f"Error checking existence of {self.model_class.__name__} {record_id}: {e}")
            raise


class QueryBuilder:
    """SQL query builder for complex queries"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.select_fields = ["*"]
        self.where_conditions = []
        self.join_clauses = []
        self.order_clauses = []
        self.group_clauses = []
        self.having_conditions = []
        self.limit_value = None
        self.offset_value = None
        self.params = []
    
    def select(self, *fields: str) -> 'QueryBuilder':
        """Set SELECT fields"""
        self.select_fields = list(fields)
        return self
    
    def where(self, condition: str, *params) -> 'QueryBuilder':
        """Add WHERE condition"""
        self.where_conditions.append(condition)
        self.params.extend(params)
        return self
    
    def join(self, table: str, on_condition: str, join_type: str = "INNER") -> 'QueryBuilder':
        """Add JOIN clause"""
        self.join_clauses.append(f"{join_type} JOIN {table} ON {on_condition}")
        return self
    
    def left_join(self, table: str, on_condition: str) -> 'QueryBuilder':
        """Add LEFT JOIN clause"""
        return self.join(table, on_condition, "LEFT")
    
    def order_by(self, field: str, direction: str = "ASC") -> 'QueryBuilder':
        """Add ORDER BY clause"""
        self.order_clauses.append(f"{field} {direction}")
        return self
    
    def group_by(self, *fields: str) -> 'QueryBuilder':
        """Add GROUP BY clause"""
        self.group_clauses.extend(fields)
        return self
    
    def having(self, condition: str, *params) -> 'QueryBuilder':
        """Add HAVING condition"""
        self.having_conditions.append(condition)
        self.params.extend(params)
        return self
    
    def limit(self, count: int) -> 'QueryBuilder':
        """Set LIMIT"""
        self.limit_value = count
        return self
    
    def offset(self, count: int) -> 'QueryBuilder':
        """Set OFFSET"""
        self.offset_value = count
        return self
    
    def build(self) -> tuple[str, tuple]:
        """Build the final query and parameters"""
        query_parts = [
            f"SELECT {', '.join(self.select_fields)}",
            f"FROM {self.table_name}"
        ]
        
        # Add JOINs
        if self.join_clauses:
            query_parts.extend(self.join_clauses)
        
        # Add WHERE
        if self.where_conditions:
            query_parts.append(f"WHERE {' AND '.join(self.where_conditions)}")
        
        # Add GROUP BY
        if self.group_clauses:
            query_parts.append(f"GROUP BY {', '.join(self.group_clauses)}")
        
        # Add HAVING
        if self.having_conditions:
            query_parts.append(f"HAVING {' AND '.join(self.having_conditions)}")
        
        # Add ORDER BY
        if self.order_clauses:
            query_parts.append(f"ORDER BY {', '.join(self.order_clauses)}")
        
        # Add LIMIT and OFFSET
        if self.limit_value is not None:
            query_parts.append(f"LIMIT {self.limit_value}")
            
        if self.offset_value is not None:
            query_parts.append(f"OFFSET {self.offset_value}")
        
        query = " ".join(query_parts)
        return query, tuple(self.params)


class DatabaseUtils:
    """Database utility functions"""
    
    @staticmethod
    def execute_script(script_path: str, db_manager: Optional[DatabaseManager] = None) -> bool:
        """Execute a SQL script file"""
        db_manager = db_manager or get_database_manager()
        
        try:
            with open(script_path, 'r') as f:
                script = f.read()
            
            # Split script into individual statements
            statements = [stmt.strip() for stmt in script.split(';') if stmt.strip()]
            
            with db_manager.transaction() as conn:
                for statement in statements:
                    if statement:
                        conn.execute(statement)
            
            logger.info(f"Successfully executed script: {script_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error executing script {script_path}: {e}")
            return False
    
    @staticmethod
    def backup_database(backup_path: str, db_manager: Optional[DatabaseManager] = None) -> bool:
        """Create a database backup"""
        db_manager = db_manager or get_database_manager()
        
        try:
            import shutil
            from pathlib import Path
            
            # Ensure backup directory exists
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy database file
            shutil.copy2(db_manager.config.database_path, backup_path)
            
            logger.info(f"Database backed up to: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return False
    
    @staticmethod
    def get_table_info(table_name: str, db_manager: Optional[DatabaseManager] = None) -> List[Dict[str, Any]]:
        """Get table schema information"""
        db_manager = db_manager or get_database_manager()
        
        try:
            query = f"PRAGMA table_info({table_name})"
            results = db_manager.execute_query(query)
            
            return [
                {
                    "column_id": row["cid"],
                    "name": row["name"],
                    "type": row["type"],
                    "not_null": bool(row["notnull"]),
                    "default_value": row["dflt_value"],
                    "primary_key": bool(row["pk"])
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error getting table info for {table_name}: {e}")
            return []
    
    @staticmethod
    def get_database_size(db_manager: Optional[DatabaseManager] = None) -> Dict[str, Any]:
        """Get database size information"""
        db_manager = db_manager or get_database_manager()
        
        try:
            # Get page count and page size
            page_count_result = db_manager.execute_query("PRAGMA page_count")
            page_size_result = db_manager.execute_query("PRAGMA page_size")
            
            page_count = page_count_result[0]["page_count"] if page_count_result else 0
            page_size = page_size_result[0]["page_size"] if page_size_result else 0
            
            total_size = page_count * page_size
            
            # Get table sizes
            tables_query = """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """
            tables = db_manager.execute_query(tables_query)
            
            table_sizes = {}
            for table in tables:
                table_name = table["name"]
                count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                count_result = db_manager.execute_query(count_query)
                table_sizes[table_name] = count_result[0]["count"] if count_result else 0
            
            return {
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "page_count": page_count,
                "page_size": page_size,
                "table_row_counts": table_sizes
            }
            
        except Exception as e:
            logger.error(f"Error getting database size: {e}")
            return {}


class TransactionManager:
    """Advanced transaction management"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or get_database_manager()
        self.savepoints = []
    
    def savepoint(self, name: str):
        """Create a savepoint"""
        query = f"SAVEPOINT {name}"
        self.db_manager.execute_command(query)
        self.savepoints.append(name)
        logger.debug(f"Created savepoint: {name}")
    
    def rollback_to_savepoint(self, name: str):
        """Rollback to a specific savepoint"""
        if name not in self.savepoints:
            raise ValueError(f"Savepoint {name} does not exist")
        
        query = f"ROLLBACK TO SAVEPOINT {name}"
        self.db_manager.execute_command(query)
        
        # Remove savepoints created after this one
        index = self.savepoints.index(name)
        self.savepoints = self.savepoints[:index + 1]
        
        logger.debug(f"Rolled back to savepoint: {name}")
    
    def release_savepoint(self, name: str):
        """Release a savepoint"""
        if name not in self.savepoints:
            raise ValueError(f"Savepoint {name} does not exist")
        
        query = f"RELEASE SAVEPOINT {name}"
        self.db_manager.execute_command(query)
        self.savepoints.remove(name)
        
        logger.debug(f"Released savepoint: {name}")

