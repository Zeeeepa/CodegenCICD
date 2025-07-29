"""
Project secrets repository implementation with encryption support
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import base64
from cryptography.fernet import Fernet
import os

from database.base import BaseRepository
from database.connection_manager import DatabaseManager
from models import ProjectSecret
from errors.exceptions import DatabaseError, ValidationError, SecurityError

logger = logging.getLogger(__name__)


class ProjectSecretsRepository(BaseRepository[ProjectSecret]):
    """Repository for project secrets with encryption/decryption"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(ProjectSecret, "project_secrets", db_manager)
        self._encryption_key = self._get_encryption_key()
        self._cipher = Fernet(self._encryption_key)
    
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key for secrets"""
        try:
            # Try to get key from environment
            key_str = os.getenv('SECRETS_ENCRYPTION_KEY')
            if key_str:
                return base64.urlsafe_b64decode(key_str.encode())
            
            # Generate new key if not found
            key = Fernet.generate_key()
            logger.warning("Generated new encryption key. Set SECRETS_ENCRYPTION_KEY environment variable for persistence.")
            return key
            
        except Exception as e:
            logger.error(f"Failed to get encryption key: {str(e)}")
            raise SecurityError("Failed to initialize encryption for secrets")
    
    def _encrypt_value(self, value: str) -> str:
        """Encrypt a secret value"""
        try:
            encrypted_bytes = self._cipher.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt secret value: {str(e)}")
            raise SecurityError("Failed to encrypt secret value")
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a secret value"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted_bytes = self._cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt secret value: {str(e)}")
            raise SecurityError("Failed to decrypt secret value")
    
    def create(self, data: Dict[str, Any]) -> ProjectSecret:
        """Create a new project secret with encryption"""
        try:
            # Validate required fields
            if not data.get('project_id') or not data.get('key_name') or not data.get('value'):
                raise ValidationError("Missing required fields: project_id, key_name, value")
            
            # Check for duplicate key name within project
            existing = self.get_by_project_and_key(data['project_id'], data['key_name'])
            if existing:
                raise ValidationError(f"Secret key '{data['key_name']}' already exists for project {data['project_id']}")
            
            # Encrypt the value
            encrypted_value = self._encrypt_value(data['value'])
            
            # Set timestamp
            now = datetime.utcnow()
            
            # Execute insert
            query = """
                INSERT INTO project_secrets (project_id, key_name, encrypted_value, created_at)
                VALUES (?, ?, ?, ?)
            """
            params = (
                data['project_id'],
                data['key_name'],
                encrypted_value,
                now
            )
            
            secret_id = self.db_manager.execute_command(query, params)
            
            # Return created secret (without decrypted value for security)
            created_secret = self.get_by_id(secret_id)
            if not created_secret:
                raise DatabaseError("Failed to retrieve created project secret")
            
            logger.info(f"Created project secret {secret_id} for project {data['project_id']}")
            return created_secret
            
        except Exception as e:
            logger.error(f"Failed to create project secret: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError, SecurityError)):
                raise
            raise DatabaseError(f"Project secret creation failed: {str(e)}")
    
    def get_by_id(self, secret_id: int) -> Optional[ProjectSecret]:
        """Get project secret by ID (returns encrypted value)"""
        try:
            query = "SELECT * FROM project_secrets WHERE id = ?"
            results = self.db_manager.execute_query(query, (secret_id,))
            
            if not results:
                return None
            
            return ProjectSecret(**results[0])
            
        except Exception as e:
            logger.error(f"Failed to get project secret {secret_id}: {str(e)}")
            raise DatabaseError(f"Failed to retrieve project secret: {str(e)}")
    
    def get_by_project_and_key(self, project_id: int, key_name: str) -> Optional[ProjectSecret]:
        """Get project secret by project ID and key name"""
        try:
            query = "SELECT * FROM project_secrets WHERE project_id = ? AND key_name = ?"
            results = self.db_manager.execute_query(query, (project_id, key_name))
            
            if not results:
                return None
            
            return ProjectSecret(**results[0])
            
        except Exception as e:
            logger.error(f"Failed to get project secret {project_id}/{key_name}: {str(e)}")
            raise DatabaseError(f"Failed to retrieve project secret: {str(e)}")
    
    def get_by_project_id(self, project_id: int) -> List[ProjectSecret]:
        """Get all secrets for a project (returns encrypted values)"""
        try:
            query = "SELECT * FROM project_secrets WHERE project_id = ? ORDER BY key_name"
            results = self.db_manager.execute_query(query, (project_id,))
            
            return [ProjectSecret(**row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get project secrets for project {project_id}: {str(e)}")
            raise DatabaseError(f"Failed to retrieve project secrets: {str(e)}")
    
    def get_decrypted_value(self, project_id: int, key_name: str) -> Optional[str]:
        """Get decrypted value for a specific secret"""
        try:
            secret = self.get_by_project_and_key(project_id, key_name)
            if not secret:
                return None
            
            return self._decrypt_value(secret.encrypted_value)
            
        except Exception as e:
            logger.error(f"Failed to get decrypted value for {project_id}/{key_name}: {str(e)}")
            if isinstance(e, SecurityError):
                raise
            raise DatabaseError(f"Failed to get secret value: {str(e)}")
    
    def get_decrypted_secrets(self, project_id: int) -> Dict[str, str]:
        """Get all decrypted secrets for a project as key-value pairs"""
        try:
            secrets = self.get_by_project_id(project_id)
            decrypted_secrets = {}
            
            for secret in secrets:
                try:
                    decrypted_value = self._decrypt_value(secret.encrypted_value)
                    decrypted_secrets[secret.key_name] = decrypted_value
                except SecurityError:
                    logger.warning(f"Failed to decrypt secret {secret.key_name} for project {project_id}")
                    # Skip corrupted secrets rather than failing entirely
                    continue
            
            return decrypted_secrets
            
        except Exception as e:
            logger.error(f"Failed to get decrypted secrets for project {project_id}: {str(e)}")
            raise DatabaseError(f"Failed to get project secrets: {str(e)}")
    
    def update(self, secret_id: int, data: Dict[str, Any]) -> Optional[ProjectSecret]:
        """Update project secret"""
        try:
            # Get existing secret
            existing = self.get_by_id(secret_id)
            if not existing:
                return None
            
            # Check for duplicate key name if key_name is being updated
            if 'key_name' in data and data['key_name'] != existing.key_name:
                duplicate = self.get_by_project_and_key(existing.project_id, data['key_name'])
                if duplicate:
                    raise ValidationError(f"Secret key '{data['key_name']}' already exists for project {existing.project_id}")
            
            # Encrypt new value if provided
            if 'value' in data:
                data['encrypted_value'] = self._encrypt_value(data['value'])
                del data['value']  # Remove plaintext value
            
            # Build update query dynamically
            update_fields = []
            params = []
            
            for field, value in data.items():
                if field in ['key_name', 'encrypted_value']:
                    update_fields.append(f"{field} = ?")
                    params.append(value)
            
            if not update_fields:
                return existing  # No valid fields to update
            
            params.append(secret_id)
            query = f"UPDATE project_secrets SET {', '.join(update_fields)} WHERE id = ?"
            
            rows_affected = self.db_manager.execute_command(query, tuple(params))
            
            if rows_affected == 0:
                return None
            
            # Return updated secret
            updated_secret = self.get_by_id(secret_id)
            logger.info(f"Updated project secret {secret_id}")
            return updated_secret
            
        except Exception as e:
            logger.error(f"Failed to update project secret {secret_id}: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError, SecurityError)):
                raise
            raise DatabaseError(f"Project secret update failed: {str(e)}")
    
    def update_or_create(self, project_id: int, key_name: str, value: str) -> ProjectSecret:
        """Update existing secret or create new one"""
        try:
            existing = self.get_by_project_and_key(project_id, key_name)
            
            if existing:
                # Update existing secret
                data = {'value': value}
                updated = self.update(existing.id, data)
                if not updated:
                    raise DatabaseError("Failed to update existing secret")
                return updated
            else:
                # Create new secret
                data = {
                    'project_id': project_id,
                    'key_name': key_name,
                    'value': value
                }
                return self.create(data)
                
        except Exception as e:
            logger.error(f"Failed to update or create secret {project_id}/{key_name}: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError, SecurityError)):
                raise
            raise DatabaseError(f"Secret update/create failed: {str(e)}")
    
    def delete(self, secret_id: int) -> bool:
        """Delete a project secret"""
        try:
            query = "DELETE FROM project_secrets WHERE id = ?"
            rows_affected = self.db_manager.execute_command(query, (secret_id,))
            
            if rows_affected > 0:
                logger.info(f"Deleted project secret {secret_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete project secret {secret_id}: {str(e)}")
            raise DatabaseError(f"Project secret deletion failed: {str(e)}")
    
    def delete_by_project_and_key(self, project_id: int, key_name: str) -> bool:
        """Delete a project secret by project ID and key name"""
        try:
            query = "DELETE FROM project_secrets WHERE project_id = ? AND key_name = ?"
            rows_affected = self.db_manager.execute_command(query, (project_id, key_name))
            
            if rows_affected > 0:
                logger.info(f"Deleted project secret {project_id}/{key_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete project secret {project_id}/{key_name}: {str(e)}")
            raise DatabaseError(f"Project secret deletion failed: {str(e)}")
    
    def delete_by_project_id(self, project_id: int) -> int:
        """Delete all secrets for a project"""
        try:
            query = "DELETE FROM project_secrets WHERE project_id = ?"
            rows_affected = self.db_manager.execute_command(query, (project_id,))
            
            logger.info(f"Deleted {rows_affected} project secrets for project {project_id}")
            return rows_affected
            
        except Exception as e:
            logger.error(f"Failed to delete project secrets for project {project_id}: {str(e)}")
            raise DatabaseError(f"Project secrets deletion failed: {str(e)}")
    
    def bulk_update_secrets(self, project_id: int, secrets: Dict[str, str]) -> List[ProjectSecret]:
        """Bulk update/create secrets for a project"""
        try:
            updated_secrets = []
            
            with self.db_manager.transaction():
                for key_name, value in secrets.items():
                    secret = self.update_or_create(project_id, key_name, value)
                    updated_secrets.append(secret)
            
            logger.info(f"Bulk updated {len(updated_secrets)} secrets for project {project_id}")
            return updated_secrets
            
        except Exception as e:
            logger.error(f"Failed to bulk update secrets for project {project_id}: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError, SecurityError)):
                raise
            raise DatabaseError(f"Bulk secret update failed: {str(e)}")

