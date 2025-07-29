"""
Encryption utilities for secure storage of secrets
"""
import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class EncryptionManager:
    def __init__(self):
        self.encryption_key = self._get_or_create_key()
        self.fernet = Fernet(self.encryption_key)
    
    def _get_or_create_key(self) -> bytes:
        """Get encryption key from environment or generate one"""
        # Try to get key from environment
        env_key = os.getenv("SECRET_ENCRYPTION_KEY")
        if env_key:
            try:
                return base64.urlsafe_b64decode(env_key.encode())
            except Exception as e:
                logger.warning(f"Invalid encryption key in environment: {e}")
        
        # Generate key from password and salt
        password = os.getenv("ENCRYPTION_PASSWORD", "default-password-change-in-production").encode()
        salt = os.getenv("ENCRYPTION_SALT", "default-salt-change-in-production").encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password))
        
        # Log warning about using default values
        if password == b"default-password-change-in-production":
            logger.warning("Using default encryption password - change in production!")
        
        return key
    
    def encrypt(self, value: str) -> str:
        """Encrypt a string value"""
        try:
            encrypted_bytes = self.fernet.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise Exception("Failed to encrypt value")
    
    def decrypt(self, encrypted_value: str) -> str:
        """Decrypt an encrypted string value"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise Exception("Failed to decrypt value")

# Global encryption manager instance
_encryption_manager = None

def get_encryption_manager() -> EncryptionManager:
    """Get the global encryption manager instance"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager

def encrypt_value(value: str) -> str:
    """Encrypt a value using the global encryption manager"""
    return get_encryption_manager().encrypt(value)

def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a value using the global encryption manager"""
    return get_encryption_manager().decrypt(encrypted_value)

def generate_encryption_key() -> str:
    """Generate a new encryption key for use in environment variables"""
    key = Fernet.generate_key()
    return base64.urlsafe_b64encode(key).decode()

if __name__ == "__main__":
    # Generate a new key for setup
    print("Generated encryption key:")
    print(generate_encryption_key())
    print("\nAdd this to your .env file as:")
    print("SECRET_ENCRYPTION_KEY=<generated_key>")

