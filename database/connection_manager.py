"""
Database Connection Manager for CodegenCICD Dashboard

This module provides comprehensive database connection management with
connection pooling, transaction handling, and automatic retry logic.
"""

import asyncio
import logging
import sqlite3
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta

import aiosqlite

logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """Database connection configuration"""
    database_path: str = "data/codegen_cicd.db"
    max_connections: int = 10
    connection_timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_wal_mode: bool = True
    enable_foreign_keys: bool = True
    busy_timeout: int = 30000  # milliseconds
    cache_size: int = -64000   # 64MB cache
    journal_mode: str = "WAL"
    synchronous: str = "NORMAL"


@dataclass
class ConnectionStats:
    """Connection pool statistics"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    total_queries: int = 0
    failed_queries: int = 0
    average_query_time: float = 0.0
    last_error: Optional[str] = None
    uptime_seconds: float = 0.0


class DatabaseError(Exception):
    """Base database error"""
    pass


class ConnectionPoolError(DatabaseError):
    """Connection pool related error"""
    pass


class TransactionError(DatabaseError):
    """Transaction related error"""
    pass


class MigrationError(DatabaseError):
    """Migration related error"""
    pass


class ConnectionPool:
    """Thread-safe SQLite connection pool"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.connections: List[sqlite3.Connection] = []
        self.available_connections: List[sqlite3.Connection] = []
        self.lock = threading.RLock()
        self.stats = ConnectionStats()
        self.start_time = time.time()
        self._closed = False
        
        # Ensure database directory exists
        db_path = Path(config.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize connection pool
        self._initialize_pool()
        
    def _initialize_pool(self):
        """Initialize the connection pool"""
        logger.info(f"Initializing connection pool with {self.config.max_connections} connections")
        
        try:
            # Create initial connections
            for i in range(min(3, self.config.max_connections)):
                conn = self._create_connection()
                self.connections.append(conn)
                self.available_connections.append(conn)
                
            self.stats.total_connections = len(self.connections)
            self.stats.idle_connections = len(self.available_connections)
            
            logger.info(f"Connection pool initialized with {len(self.connections)} connections")
            
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise ConnectionPoolError(f"Pool initialization failed: {e}")
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimal settings"""
        try:
            conn = sqlite3.connect(
                self.config.database_path,
                timeout=self.config.connection_timeout,
                check_same_thread=False
            )
            
            # Configure connection for optimal performance
            conn.execute(f"PRAGMA journal_mode = {self.config.journal_mode}")
            conn.execute(f"PRAGMA synchronous = {self.config.synchronous}")
            conn.execute(f"PRAGMA cache_size = {self.config.cache_size}")
            conn.execute(f"PRAGMA busy_timeout = {self.config.busy_timeout}")
            
            if self.config.enable_foreign_keys:
                conn.execute("PRAGMA foreign_keys = ON")
                
            # Enable row factory for dict-like access
            conn.row_factory = sqlite3.Row
            
            return conn
            
        except Exception as e:
            self.stats.failed_connections += 1
            self.stats.last_error = str(e)
            logger.error(f"Failed to create database connection: {e}")
            raise ConnectionPoolError(f"Connection creation failed: {e}")
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        if self._closed:
            raise ConnectionPoolError("Connection pool is closed")
            
        conn = None
        try:
            with self.lock:
                # Try to get an available connection
                if self.available_connections:
                    conn = self.available_connections.pop()
                    self.stats.active_connections += 1
                    self.stats.idle_connections -= 1
                    
                # Create new connection if pool not at capacity
                elif len(self.connections) < self.config.max_connections:
                    conn = self._create_connection()
                    self.connections.append(conn)
                    self.stats.total_connections += 1
                    self.stats.active_connections += 1
                    
                else:
                    raise ConnectionPoolError("Connection pool exhausted")
            
            # Test connection
            try:
                conn.execute("SELECT 1").fetchone()
            except sqlite3.Error:
                # Connection is stale, create a new one
                conn.close()
                conn = self._create_connection()
                
            yield conn
            
        except Exception as e:
            self.stats.last_error = str(e)
            logger.error(f"Error getting connection: {e}")
            raise
            
        finally:
            # Return connection to pool
            if conn:
                with self.lock:
                    if not self._closed and conn in self.connections:
                        self.available_connections.append(conn)
                        self.stats.active_connections -= 1
                        self.stats.idle_connections += 1
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results"""
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                    
                results = [dict(row) for row in cursor.fetchall()]
                
                # Update stats
                query_time = time.time() - start_time
                self.stats.total_queries += 1
                self.stats.average_query_time = (
                    (self.stats.average_query_time * (self.stats.total_queries - 1) + query_time) 
                    / self.stats.total_queries
                )
                
                return results
                
        except Exception as e:
            self.stats.failed_queries += 1
            self.stats.last_error = str(e)
            logger.error(f"Query execution failed: {e}")
            raise DatabaseError(f"Query failed: {e}")
    
    def execute_command(self, command: str, params: Optional[tuple] = None) -> int:
        """Execute an INSERT, UPDATE, or DELETE command"""
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(command, params)
                else:
                    cursor.execute(command)
                    
                conn.commit()
                
                # Update stats
                query_time = time.time() - start_time
                self.stats.total_queries += 1
                self.stats.average_query_time = (
                    (self.stats.average_query_time * (self.stats.total_queries - 1) + query_time) 
                    / self.stats.total_queries
                )
                
                return cursor.rowcount
                
        except Exception as e:
            self.stats.failed_queries += 1
            self.stats.last_error = str(e)
            logger.error(f"Command execution failed: {e}")
            raise DatabaseError(f"Command failed: {e}")
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions"""
        with self.get_connection() as conn:
            try:
                conn.execute("BEGIN")
                yield conn
                conn.commit()
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction rolled back: {e}")
                raise TransactionError(f"Transaction failed: {e}")
    
    def get_stats(self) -> ConnectionStats:
        """Get connection pool statistics"""
        with self.lock:
            self.stats.uptime_seconds = time.time() - self.start_time
            return self.stats
    
    def close(self):
        """Close all connections in the pool"""
        logger.info("Closing connection pool")
        
        with self.lock:
            self._closed = True
            
            for conn in self.connections:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
                    
            self.connections.clear()
            self.available_connections.clear()
            self.stats.total_connections = 0
            self.stats.active_connections = 0
            self.stats.idle_connections = 0


class AsyncConnectionPool:
    """Async SQLite connection pool using aiosqlite"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.connections: List[aiosqlite.Connection] = []
        self.available_connections: List[aiosqlite.Connection] = []
        self.lock = asyncio.Lock()
        self.stats = ConnectionStats()
        self.start_time = time.time()
        self._closed = False
        
        # Ensure database directory exists
        db_path = Path(config.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def _create_connection(self) -> aiosqlite.Connection:
        """Create a new async database connection"""
        try:
            conn = await aiosqlite.connect(
                self.config.database_path,
                timeout=self.config.connection_timeout
            )
            
            # Configure connection
            await conn.execute(f"PRAGMA journal_mode = {self.config.journal_mode}")
            await conn.execute(f"PRAGMA synchronous = {self.config.synchronous}")
            await conn.execute(f"PRAGMA cache_size = {self.config.cache_size}")
            await conn.execute(f"PRAGMA busy_timeout = {self.config.busy_timeout}")
            
            if self.config.enable_foreign_keys:
                await conn.execute("PRAGMA foreign_keys = ON")
                
            # Set row factory
            conn.row_factory = aiosqlite.Row
            
            return conn
            
        except Exception as e:
            self.stats.failed_connections += 1
            self.stats.last_error = str(e)
            logger.error(f"Failed to create async connection: {e}")
            raise ConnectionPoolError(f"Async connection creation failed: {e}")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get an async connection from the pool"""
        if self._closed:
            raise ConnectionPoolError("Async connection pool is closed")
            
        conn = None
        try:
            async with self.lock:
                # Try to get an available connection
                if self.available_connections:
                    conn = self.available_connections.pop()
                    self.stats.active_connections += 1
                    self.stats.idle_connections -= 1
                    
                # Create new connection if pool not at capacity
                elif len(self.connections) < self.config.max_connections:
                    conn = await self._create_connection()
                    self.connections.append(conn)
                    self.stats.total_connections += 1
                    self.stats.active_connections += 1
                    
                else:
                    raise ConnectionPoolError("Async connection pool exhausted")
            
            # Test connection
            try:
                await conn.execute("SELECT 1")
            except Exception:
                # Connection is stale, create a new one
                await conn.close()
                conn = await self._create_connection()
                
            yield conn
            
        except Exception as e:
            self.stats.last_error = str(e)
            logger.error(f"Error getting async connection: {e}")
            raise
            
        finally:
            # Return connection to pool
            if conn:
                async with self.lock:
                    if not self._closed and conn in self.connections:
                        self.available_connections.append(conn)
                        self.stats.active_connections -= 1
                        self.stats.idle_connections += 1
    
    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute an async SELECT query"""
        start_time = time.time()
        
        try:
            async with self.get_connection() as conn:
                if params:
                    cursor = await conn.execute(query, params)
                else:
                    cursor = await conn.execute(query)
                    
                rows = await cursor.fetchall()
                results = [dict(row) for row in rows]
                
                # Update stats
                query_time = time.time() - start_time
                self.stats.total_queries += 1
                self.stats.average_query_time = (
                    (self.stats.average_query_time * (self.stats.total_queries - 1) + query_time) 
                    / self.stats.total_queries
                )
                
                return results
                
        except Exception as e:
            self.stats.failed_queries += 1
            self.stats.last_error = str(e)
            logger.error(f"Async query execution failed: {e}")
            raise DatabaseError(f"Async query failed: {e}")
    
    async def execute_command(self, command: str, params: Optional[tuple] = None) -> int:
        """Execute an async INSERT, UPDATE, or DELETE command"""
        start_time = time.time()
        
        try:
            async with self.get_connection() as conn:
                if params:
                    cursor = await conn.execute(command, params)
                else:
                    cursor = await conn.execute(command)
                    
                await conn.commit()
                
                # Update stats
                query_time = time.time() - start_time
                self.stats.total_queries += 1
                self.stats.average_query_time = (
                    (self.stats.average_query_time * (self.stats.total_queries - 1) + query_time) 
                    / self.stats.total_queries
                )
                
                return cursor.rowcount
                
        except Exception as e:
            self.stats.failed_queries += 1
            self.stats.last_error = str(e)
            logger.error(f"Async command execution failed: {e}")
            raise DatabaseError(f"Async command failed: {e}")
    
    @asynccontextmanager
    async def transaction(self):
        """Async context manager for database transactions"""
        async with self.get_connection() as conn:
            try:
                await conn.execute("BEGIN")
                yield conn
                await conn.commit()
                
            except Exception as e:
                await conn.rollback()
                logger.error(f"Async transaction rolled back: {e}")
                raise TransactionError(f"Async transaction failed: {e}")
    
    async def close(self):
        """Close all async connections in the pool"""
        logger.info("Closing async connection pool")
        
        async with self.lock:
            self._closed = True
            
            for conn in self.connections:
                try:
                    await conn.close()
                except Exception as e:
                    logger.warning(f"Error closing async connection: {e}")
                    
            self.connections.clear()
            self.available_connections.clear()
            self.stats.total_connections = 0
            self.stats.active_connections = 0
            self.stats.idle_connections = 0


class DatabaseManager:
    """Main database manager with both sync and async support"""
    
    def __init__(self, config: Optional[ConnectionConfig] = None):
        self.config = config or ConnectionConfig()
        self.sync_pool = ConnectionPool(self.config)
        self.async_pool = AsyncConnectionPool(self.config)
        
        logger.info("Database manager initialized")
    
    # Sync methods
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a synchronous query"""
        return self.sync_pool.execute_query(query, params)
    
    def execute_command(self, command: str, params: Optional[tuple] = None) -> int:
        """Execute a synchronous command"""
        return self.sync_pool.execute_command(command, params)
    
    @contextmanager
    def transaction(self):
        """Synchronous transaction context manager"""
        with self.sync_pool.transaction() as conn:
            yield conn
    
    # Async methods
    async def async_execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute an asynchronous query"""
        return await self.async_pool.execute_query(query, params)
    
    async def async_execute_command(self, command: str, params: Optional[tuple] = None) -> int:
        """Execute an asynchronous command"""
        return await self.async_pool.execute_command(command, params)
    
    @asynccontextmanager
    async def async_transaction(self):
        """Asynchronous transaction context manager"""
        async with self.async_pool.transaction() as conn:
            yield conn
    
    # Utility methods
    def get_stats(self) -> Dict[str, ConnectionStats]:
        """Get statistics for both pools"""
        return {
            "sync": self.sync_pool.get_stats(),
            "async": self.async_pool.stats
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            # Test sync connection
            sync_result = self.execute_query("SELECT 1 as test")
            sync_healthy = len(sync_result) == 1 and sync_result[0]["test"] == 1
            
            stats = self.get_stats()
            
            return {
                "healthy": sync_healthy,
                "sync_pool_healthy": sync_healthy,
                "stats": stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def close(self):
        """Close both connection pools"""
        logger.info("Closing database manager")
        self.sync_pool.close()
        asyncio.create_task(self.async_pool.close())


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager(config: Optional[ConnectionConfig] = None) -> DatabaseManager:
    """Get or create the global database manager instance"""
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager(config)
        
    return _db_manager


def close_database_manager():
    """Close the global database manager"""
    global _db_manager
    
    if _db_manager:
        _db_manager.close()
        _db_manager = None

