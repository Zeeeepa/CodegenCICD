"""
Encryption utilities for secure secrets management
"""
import base64
import os
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import structlog

from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class EncryptionManager:
    """Manages encryption and decryption of sensitive data"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize encryption manager with key"""
        self._key = encryption_key or settings.secret_encryption_key
        if not self._key:
            raise ValueError("Encryption key must be provided")
        
        self._fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """Create Fernet instance from key"""
        try:
            # If key is already base64 encoded Fernet key, use it directly
            if len(self._key) == 44 and self._key.endswith('='):
                key = self._key.encode()
            else:
                # Derive key from password using PBKDF2
                key = self._derive_key_from_password(self._key)
            
            return Fernet(key)
        except Exception as e:
            logger.error("Failed to create Fernet instance", error=str(e))
            raise ValueError("Invalid encryption key format")
    
    def _derive_key_from_password(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        if salt is None:
            # Use a fixed salt for consistency (in production, consider using per-secret salts)
            salt = b"codegencd_salt_2024"
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """Encrypt data and return base64 encoded string"""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            encrypted_data = self._fernet.encrypt(data)
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error("Encryption failed", error=str(e))
            raise ValueError("Failed to encrypt data")
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt base64 encoded encrypted data"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self._fernet.decrypt(encrypted_bytes)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            raise ValueError("Failed to decrypt data")
    
    def encrypt_dict(self, data: dict, keys_to_encrypt: list) -> dict:
        """Encrypt specific keys in a dictionary"""
        result = data.copy()
        for key in keys_to_encrypt:
            if key in result and result[key] is not None:
                result[key] = self.encrypt(str(result[key]))
        return result
    
    def decrypt_dict(self, data: dict, keys_to_decrypt: list) -> dict:
        """Decrypt specific keys in a dictionary"""
        result = data.copy()
        for key in keys_to_decrypt:
            if key in result and result[key] is not None:
                try:
                    result[key] = self.decrypt(result[key])
                except ValueError:
                    # If decryption fails, leave the value as is (might not be encrypted)
                    logger.warning(f"Failed to decrypt key: {key}")
        return result
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet key"""
        return Fernet.generate_key().decode()
    
    @staticmethod
    def is_encrypted(data: str) -> bool:
        """Check if data appears to be encrypted (basic heuristic)"""
        try:
            # Encrypted data should be base64 encoded and have specific characteristics
            decoded = base64.urlsafe_b64decode(data.encode('utf-8'))
            # Fernet encrypted data has a specific structure and minimum length
            return len(decoded) >= 57  # Minimum Fernet token length
        except Exception:
            return False


# Global encryption manager instance
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """Get global encryption manager instance"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def encrypt_secret(data: Union[str, bytes]) -> str:
    """Convenience function to encrypt data"""
    return get_encryption_manager().encrypt(data)


def decrypt_secret(encrypted_data: str) -> str:
    """Convenience function to decrypt data"""
    return get_encryption_manager().decrypt(encrypted_data)


def generate_encryption_key() -> str:
    """Generate a new encryption key"""
    return EncryptionManager.generate_key()


# Environment variable encryption utilities
class EnvEncryption:
    """Utilities for encrypting environment variables"""
    
    @staticmethod
    def encrypt_env_file(input_file: str, output_file: str, keys_to_encrypt: list):
        """Encrypt specific keys in an environment file"""
        encryption_manager = get_encryption_manager()
        
        with open(input_file, 'r') as f:
            lines = f.readlines()
        
        encrypted_lines = []
        for line in lines:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                if key in keys_to_encrypt:
                    encrypted_value = encryption_manager.encrypt(value)
                    encrypted_lines.append(f"{key}={encrypted_value}\n")
                else:
                    encrypted_lines.append(f"{line}\n")
            else:
                encrypted_lines.append(f"{line}\n")
        
        with open(output_file, 'w') as f:
            f.writelines(encrypted_lines)
    
    @staticmethod
    def decrypt_env_file(input_file: str, output_file: str, keys_to_decrypt: list):
        """Decrypt specific keys in an environment file"""
        encryption_manager = get_encryption_manager()
        
        with open(input_file, 'r') as f:
            lines = f.readlines()
        
        decrypted_lines = []
        for line in lines:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                if key in keys_to_decrypt:
                    try:
                        decrypted_value = encryption_manager.decrypt(value)
                        decrypted_lines.append(f"{key}={decrypted_value}\n")
                    except ValueError:
                        # If decryption fails, keep original value
                        decrypted_lines.append(f"{line}\n")
                else:
                    decrypted_lines.append(f"{line}\n")
            else:
                decrypted_lines.append(f"{line}\n")
        
        with open(output_file, 'w') as f:
            f.writelines(decrypted_lines)

