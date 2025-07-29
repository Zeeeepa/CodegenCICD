"""
Database Migration Manager

This module handles database schema migrations with version tracking,
rollback capabilities, and comprehensive migration management.
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from database.connection_manager import get_database_manager, DatabaseManager

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Migration-related error"""
    pass


class Migration:
    """Represents a single database migration"""
    
    def __init__(self, version: str, name: str, file_path: Path):
        self.version = version
        self.name = name
        self.file_path = file_path
        self.up_sql = ""
        self.down_sql = ""
        self._parse_migration_file()
    
    def _parse_migration_file(self):
        """Parse migration file to extract UP and DOWN SQL"""
        try:
            with open(self.file_path, 'r') as f:
                content = f.read()
            
            # Split on migration markers
            up_match = re.search(r'-- Migration UP\s*\n(.*?)(?=-- Migration DOWN|$)', content, re.DOTALL)
            down_match = re.search(r'-- Migration DOWN.*?\n(.*?)(?=-- |$)', content, re.DOTALL)
            
            if up_match:
                self.up_sql = up_match.group(1).strip()
            else:
                # If no explicit UP section, use entire file
                self.up_sql = content.strip()
            
            if down_match:
                self.down_sql = down_match.group(1).strip()
            
        except Exception as e:
            logger.error(f"Error parsing migration file {self.file_path}: {e}")
            raise MigrationError(f"Failed to parse migration file: {e}")
    
    def __str__(self):
        return f"Migration {self.version}: {self.name}"
    
    def __repr__(self):
        return f"Migration(version='{self.version}', name='{self.name}')"


class MigrationManager:
    """Manages database migrations"""
    
    def __init__(self, migrations_dir: str = "database/migrations", db_manager: Optional[DatabaseManager] = None):
        self.migrations_dir = Path(migrations_dir)
        self.db_manager = db_manager or get_database_manager()
        self._ensure_migrations_table()
    
    def _ensure_migrations_table(self):
        """Ensure the schema_migrations table exists"""
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                migration_name TEXT,
                checksum TEXT
            )
        """
        
        try:
            self.db_manager.execute_command(create_table_sql)
            logger.debug("Schema migrations table ensured")
            
        except Exception as e:
            logger.error(f"Error creating schema_migrations table: {e}")
            raise MigrationError(f"Failed to create migrations table: {e}")
    
    def _calculate_checksum(self, content: str) -> str:
        """Calculate MD5 checksum of migration content"""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()
    
    def discover_migrations(self) -> List[Migration]:
        """Discover all migration files in the migrations directory"""
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory does not exist: {self.migrations_dir}")
            return []
        
        migrations = []
        
        # Pattern to match migration files: 001_migration_name.sql
        pattern = re.compile(r'^(\d{3})_(.+)\.sql$')
        
        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            match = pattern.match(file_path.name)
            if match:
                version = match.group(1)
                name = match.group(2).replace('_', ' ').title()
                
                migration = Migration(version, name, file_path)
                migrations.append(migration)
                
        logger.info(f"Discovered {len(migrations)} migration files")
        return migrations
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions"""
        try:
            query = "SELECT version FROM schema_migrations ORDER BY version"
            results = self.db_manager.execute_query(query)
            return [row["version"] for row in results]
            
        except Exception as e:
            logger.error(f"Error getting applied migrations: {e}")
            raise MigrationError(f"Failed to get applied migrations: {e}")
    
    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending (unapplied) migrations"""
        all_migrations = self.discover_migrations()
        applied_versions = set(self.get_applied_migrations())
        
        pending = [m for m in all_migrations if m.version not in applied_versions]
        
        logger.info(f"Found {len(pending)} pending migrations")
        return pending
    
    def apply_migration(self, migration: Migration) -> bool:
        """Apply a single migration"""
        logger.info(f"Applying migration: {migration}")
        
        try:
            # Calculate checksum
            checksum = self._calculate_checksum(migration.up_sql)
            
            with self.db_manager.transaction() as conn:
                # Execute migration SQL
                if migration.up_sql:
                    # Split into individual statements
                    statements = [stmt.strip() for stmt in migration.up_sql.split(';') if stmt.strip()]
                    
                    for statement in statements:
                        if statement:
                            conn.execute(statement)
                
                # Record migration as applied
                conn.execute(
                    """
                    INSERT INTO schema_migrations (version, migration_name, checksum)
                    VALUES (?, ?, ?)
                    """,
                    (migration.version, migration.name, checksum)
                )
            
            logger.info(f"Successfully applied migration: {migration}")
            return True
            
        except Exception as e:
            logger.error(f"Error applying migration {migration}: {e}")
            raise MigrationError(f"Failed to apply migration {migration.version}: {e}")
    
    def rollback_migration(self, migration: Migration) -> bool:
        """Rollback a single migration"""
        logger.info(f"Rolling back migration: {migration}")
        
        if not migration.down_sql:
            raise MigrationError(f"Migration {migration.version} has no rollback SQL")
        
        try:
            with self.db_manager.transaction() as conn:
                # Execute rollback SQL
                statements = [stmt.strip() for stmt in migration.down_sql.split(';') if stmt.strip()]
                
                for statement in statements:
                    if statement:
                        conn.execute(statement)
                
                # Remove migration record
                conn.execute(
                    "DELETE FROM schema_migrations WHERE version = ?",
                    (migration.version,)
                )
            
            logger.info(f"Successfully rolled back migration: {migration}")
            return True
            
        except Exception as e:
            logger.error(f"Error rolling back migration {migration}: {e}")
            raise MigrationError(f"Failed to rollback migration {migration.version}: {e}")
    
    def migrate_up(self, target_version: Optional[str] = None) -> int:
        """Apply all pending migrations up to target version"""
        pending_migrations = self.get_pending_migrations()
        
        if target_version:
            # Filter migrations up to target version
            pending_migrations = [
                m for m in pending_migrations 
                if m.version <= target_version
            ]
        
        if not pending_migrations:
            logger.info("No pending migrations to apply")
            return 0
        
        applied_count = 0
        
        for migration in pending_migrations:
            try:
                self.apply_migration(migration)
                applied_count += 1
                
            except Exception as e:
                logger.error(f"Migration failed at {migration.version}: {e}")
                raise
        
        logger.info(f"Applied {applied_count} migrations")
        return applied_count
    
    def migrate_down(self, target_version: str) -> int:
        """Rollback migrations down to target version"""
        applied_migrations = self.get_applied_migrations()
        all_migrations = {m.version: m for m in self.discover_migrations()}
        
        # Find migrations to rollback (in reverse order)
        to_rollback = [
            version for version in reversed(applied_migrations)
            if version > target_version
        ]
        
        if not to_rollback:
            logger.info(f"No migrations to rollback to version {target_version}")
            return 0
        
        rolled_back_count = 0
        
        for version in to_rollback:
            if version in all_migrations:
                migration = all_migrations[version]
                try:
                    self.rollback_migration(migration)
                    rolled_back_count += 1
                    
                except Exception as e:
                    logger.error(f"Rollback failed at {version}: {e}")
                    raise
            else:
                logger.warning(f"Migration file not found for version {version}")
        
        logger.info(f"Rolled back {rolled_back_count} migrations")
        return rolled_back_count
    
    def get_migration_status(self) -> Dict[str, any]:
        """Get comprehensive migration status"""
        all_migrations = self.discover_migrations()
        applied_versions = set(self.get_applied_migrations())
        
        status = {
            "total_migrations": len(all_migrations),
            "applied_migrations": len(applied_versions),
            "pending_migrations": len(all_migrations) - len(applied_versions),
            "current_version": max(applied_versions) if applied_versions else None,
            "latest_version": max(m.version for m in all_migrations) if all_migrations else None,
            "migrations": []
        }
        
        for migration in all_migrations:
            migration_info = {
                "version": migration.version,
                "name": migration.name,
                "applied": migration.version in applied_versions,
                "file_path": str(migration.file_path),
                "has_rollback": bool(migration.down_sql)
            }
            status["migrations"].append(migration_info)
        
        return status
    
    def validate_migrations(self) -> List[Dict[str, any]]:
        """Validate migration integrity"""
        issues = []
        
        try:
            # Check for applied migrations without files
            applied_versions = set(self.get_applied_migrations())
            available_versions = {m.version for m in self.discover_migrations()}
            
            missing_files = applied_versions - available_versions
            for version in missing_files:
                issues.append({
                    "type": "missing_file",
                    "version": version,
                    "message": f"Migration {version} is applied but file is missing"
                })
            
            # Check for checksum mismatches
            query = "SELECT version, checksum FROM schema_migrations"
            applied_checksums = {
                row["version"]: row["checksum"] 
                for row in self.db_manager.execute_query(query)
            }
            
            for migration in self.discover_migrations():
                if migration.version in applied_checksums:
                    current_checksum = self._calculate_checksum(migration.up_sql)
                    stored_checksum = applied_checksums[migration.version]
                    
                    if current_checksum != stored_checksum:
                        issues.append({
                            "type": "checksum_mismatch",
                            "version": migration.version,
                            "message": f"Migration {migration.version} has been modified after application"
                        })
            
            # Check for version gaps
            all_migrations = self.discover_migrations()
            if all_migrations:
                versions = [int(m.version) for m in all_migrations]
                expected_versions = list(range(1, max(versions) + 1))
                actual_versions = sorted(versions)
                
                missing_versions = set(expected_versions) - set(actual_versions)
                for version in missing_versions:
                    issues.append({
                        "type": "version_gap",
                        "version": f"{version:03d}",
                        "message": f"Migration version {version:03d} is missing"
                    })
            
        except Exception as e:
            issues.append({
                "type": "validation_error",
                "version": None,
                "message": f"Error during validation: {e}"
            })
        
        return issues
    
    def create_migration(self, name: str, up_sql: str = "", down_sql: str = "") -> Path:
        """Create a new migration file"""
        # Determine next version number
        existing_migrations = self.discover_migrations()
        if existing_migrations:
            last_version = max(int(m.version) for m in existing_migrations)
            next_version = f"{last_version + 1:03d}"
        else:
            next_version = "001"
        
        # Create filename
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
        filename = f"{next_version}_{safe_name}.sql"
        file_path = self.migrations_dir / filename
        
        # Ensure migrations directory exists
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        
        # Create migration file content
        content = f"""-- ============================================================================
-- Migration {next_version}: {name}
-- ============================================================================
-- Created: {datetime.now().isoformat()}
-- ============================================================================

-- Migration UP
-- ============================================================================
{up_sql or '-- Add your UP migration SQL here'}

-- ============================================================================
-- Migration DOWN (Rollback)
-- ============================================================================
-- To rollback this migration, run the following:
/*
{down_sql or '-- Add your DOWN migration SQL here'}
*/
"""
        
        # Write migration file
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Created migration file: {file_path}")
        return file_path


def create_migration_manager(migrations_dir: str = "database/migrations") -> MigrationManager:
    """Create a migration manager instance"""
    return MigrationManager(migrations_dir)

