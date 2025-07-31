"""
Project Secrets Repository - CRUD operations for project_secrets table with encryption
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import sqlite3
import logging
import base64
from cryptography.fernet import Fernet
import os

from ..models.project import ProjectSecret
from ..database import get_database_connection

logger = logging.getLogger(__name__)


class ProjectSecretsRepository:
    """Repository for ProjectSecret entity with encryption/decryption"""
    
    def __init__(self):
        self.table_name = "project_secrets"
        self._encryption_key = self._get_encryption_key()
        self._cipher = Fernet(self._encryption_key)
    
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key"""
        key_env = os.getenv('CICD_ENCRYPTION_KEY')
        if key_env:
            return base64.urlsafe_b64decode(key_env.encode())
        
        # Generate new key for development
        key = Fernet.generate_key()
        logger.warning("Using generated encryption key. Set CICD_ENCRYPTION_KEY environment variable for production.")
        return key
    
    def _encrypt_value(self, value: str) -> str:
        """Encrypt a secret value"""
        try:
            encrypted = self._cipher.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Error encrypting value: {e}")
            raise Exception("Failed to encrypt secret value")
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a secret value"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted = self._cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Error decrypting value: {e}")
            raise Exception("Failed to decrypt secret value")
    
    def create(self, data: Dict[str, Any]) -> ProjectSecret:
        """Create new project secret with encryption"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                # Encrypt the value
                if 'value' in data:
                    data['encrypted_value'] = self._encrypt_value(data['value'])
                    del data['value']  # Remove plain text value
                
                # Prepare data with timestamps
                now = datetime.utcnow().isoformat()
                data['created_at'] = now
                
                # Insert secret
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
                
                cursor.execute(query, list(data.values()))
                secret_id = cursor.lastrowid
                
                conn.commit()
                
                # Return created secret (without decrypted value for security)
                return self.get_by_id(secret_id, decrypt=False)
                
        except sqlite3.Error as e:
            logger.error(f"Database error creating project secret: {e}")
            raise Exception(f"Failed to create project secret: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating project secret: {e}")
            raise
    
    def get_by_id(self, secret_id: int, decrypt: bool = False) -> Optional[ProjectSecret]:
        """Get project secret by ID"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                query = f"SELECT * FROM {self.table_name} WHERE id = ?"
                cursor.execute(query, (secret_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_secret(row, cursor.description, decrypt)
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Database error getting project secret {secret_id}: {e}")
            raise Exception(f"Failed to get project secret: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting project secret {secret_id}: {e}")
            raise
    
    def get_by_project_id(self, project_id: int, decrypt: bool = False) -> List[ProjectSecret]:
        """Get all secrets for a project"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                query = f"SELECT * FROM {self.table_name} WHERE project_id = ? ORDER BY key_name"
                cursor.execute(query, (project_id,))
                rows = cursor.fetchall()
                
                return [self._row_to_secret(row, cursor.description, decrypt) for row in rows]
                
        except sqlite3.Error as e:
            logger.error(f"Database error getting secrets for project {project_id}: {e}")
            raise Exception(f"Failed to get project secrets: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting secrets for project {project_id}: {e}")
            raise
    
    def get_secret_value(self, project_id: int, key_name: str) -> Optional[str]:
        """Get decrypted secret value by project ID and key name"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                query = f"SELECT encrypted_value FROM {self.table_name} WHERE project_id = ? AND key_name = ?"
                cursor.execute(query, (project_id, key_name))
                row = cursor.fetchone()
                
                if row:
                    return self._decrypt_value(row[0])
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Database error getting secret value {project_id}/{key_name}: {e}")
            raise Exception(f"Failed to get secret value: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting secret value {project_id}/{key_name}: {e}")
            raise
    
    def update(self, secret_id: int, data: Dict[str, Any]) -> Optional[ProjectSecret]:
        """Update project secret"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                # Encrypt value if provided
                if 'value' in data:
                    data['encrypted_value'] = self._encrypt_value(data['value'])
                    del data['value']  # Remove plain text value
                
                # Build update query
                set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
                query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?"
                
                values = list(data.values()) + [secret_id]
                cursor.execute(query, values)
                
                if cursor.rowcount == 0:
                    return None
                
                conn.commit()
                
                # Return updated secret (without decrypted value)
                return self.get_by_id(secret_id, decrypt=False)
                
        except sqlite3.Error as e:
            logger.error(f"Database error updating project secret {secret_id}: {e}")
            raise Exception(f"Failed to update project secret: {str(e)}")
        except Exception as e:
            logger.error(f"Error updating project secret {secret_id}: {e}")
            raise
    
    def update_project_secrets(self, project_id: int, secrets: List[Dict[str, str]]) -> List[ProjectSecret]:
        """Update all secrets for a project (replace existing)"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                # Delete existing secrets
                cursor.execute(f"DELETE FROM {self.table_name} WHERE project_id = ?", (project_id,))
                
                # Insert new secrets
                created_secrets = []
                for secret_data in secrets:
                    secret_data['project_id'] = project_id
                    
                    # Encrypt the value
                    encrypted_value = self._encrypt_value(secret_data['value'])
                    
                    # Insert secret
                    now = datetime.utcnow().isoformat()
                    cursor.execute(
                        f"INSERT INTO {self.table_name} (project_id, key_name, encrypted_value, created_at) VALUES (?, ?, ?, ?)",
                        (project_id, secret_data['key_name'], encrypted_value, now)
                    )
                    
                    secret_id = cursor.lastrowid
                    created_secrets.append(self._create_secret_model(secret_id, project_id, secret_data['key_name'], encrypted_value, now))
                
                conn.commit()
                return created_secrets
                
        except sqlite3.Error as e:
            logger.error(f"Database error updating secrets for project {project_id}: {e}")
            raise Exception(f"Failed to update project secrets: {str(e)}")
        except Exception as e:
            logger.error(f"Error updating secrets for project {project_id}: {e}")
            raise
    
    def delete(self, secret_id: int) -> bool:
        """Delete project secret"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                query = f"DELETE FROM {self.table_name} WHERE id = ?"
                cursor.execute(query, (secret_id,))
                
                deleted = cursor.rowcount > 0
                conn.commit()
                
                return deleted
                
        except sqlite3.Error as e:
            logger.error(f"Database error deleting project secret {secret_id}: {e}")
            raise Exception(f"Failed to delete project secret: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting project secret {secret_id}: {e}")
            raise
    
    def delete_by_project_id(self, project_id: int) -> bool:
        """Delete all secrets for a project"""
        try:
            with get_database_connection() as conn:
                cursor = conn.cursor()
                
                query = f"DELETE FROM {self.table_name} WHERE project_id = ?"
                cursor.execute(query, (project_id,))
                
                deleted = cursor.rowcount > 0
                conn.commit()
                
                return deleted
                
        except sqlite3.Error as e:
            logger.error(f"Database error deleting secrets for project {project_id}: {e}")
            raise Exception(f"Failed to delete project secrets: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting secrets for project {project_id}: {e}")
            raise
    
    def _row_to_secret(self, row: tuple, description: List, decrypt: bool = False) -> ProjectSecret:
        """Convert database row to ProjectSecret model"""
        try:
            # Create dict from row data
            columns = [col[0] for col in description]
            data = dict(zip(columns, row))
            
            # Decrypt value if requested (for internal use only)
            if decrypt and 'encrypted_value' in data:
                try:
                    data['decrypted_value'] = self._decrypt_value(data['encrypted_value'])
                except Exception:
                    data['decrypted_value'] = None
            
            return ProjectSecret(**data)
            
        except Exception as e:
            logger.error(f"Error converting row to project secret: {e}")
            raise Exception(f"Failed to convert database row: {str(e)}")
    
    def _create_secret_model(self, secret_id: int, project_id: int, key_name: str, encrypted_value: str, created_at: str) -> ProjectSecret:
        """Create ProjectSecret model from components"""
        return ProjectSecret(
            id=secret_id,
            project_id=project_id,
            key_name=key_name,
            encrypted_value=encrypted_value,
            created_at=created_at
        )

