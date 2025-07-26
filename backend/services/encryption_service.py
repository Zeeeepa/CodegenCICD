"""
Encryption service for secure secrets management
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionService:
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)

    def _get_or_create_key(self):
        """Get encryption key from environment or generate one"""
        # In production, this should be stored securely (e.g., AWS KMS, HashiCorp Vault)
        encryption_key = os.getenv("ENCRYPTION_KEY")
        
        if encryption_key:
            return encryption_key.encode()
        
        # Generate key from password and salt
        password = os.getenv("SECRET_KEY", "default-secret-key-change-in-production").encode()
        salt = os.getenv("ENCRYPTION_SALT", "default-salt-change-in-production").encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string"""
        if not plaintext:
            return ""
        
        encrypted_data = self.cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()

    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt an encrypted string"""
        if not encrypted_text:
            return ""
        
        try:
            encrypted_data = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return decrypted_data.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {str(e)}")


# Global encryption service instance
encryption_service = EncryptionService()


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext value"""
    return encryption_service.encrypt(plaintext)


def decrypt_value(encrypted_text: str) -> str:
    """Decrypt an encrypted value"""
    return encryption_service.decrypt(encrypted_text)
