"""
Secrets management for secure storage of environment variables
"""
import os
import json
import base64
from typing import Dict, Any
from cryptography.fernet import Fernet
import structlog

logger = structlog.get_logger(__name__)


class SecretsManager:
    """Secure secrets management"""
    
    def __init__(self):
        # Get encryption key from environment or generate one
        self.encryption_key = os.getenv("SECRETS_ENCRYPTION_KEY")
        if not self.encryption_key:
            # Generate a new key (in production, this should be stored securely)
            self.encryption_key = Fernet.generate_key().decode()
            logger.warning("Generated new encryption key - store SECRETS_ENCRYPTION_KEY in environment")
        
        if isinstance(self.encryption_key, str):
            self.encryption_key = self.encryption_key.encode()
        
        self.cipher = Fernet(self.encryption_key)
    
    def encrypt_secrets(self, secrets: Dict[str, str]) -> Dict[str, Any]:
        """Encrypt a dictionary of secrets"""
        try:
            if not secrets:
                return {}
            
            # Convert to JSON string
            secrets_json = json.dumps(secrets)
            
            # Encrypt
            encrypted_data = self.cipher.encrypt(secrets_json.encode())
            
            # Encode to base64 for storage
            encrypted_b64 = base64.b64encode(encrypted_data).decode()
            
            return {
                "encrypted": True,
                "data": encrypted_b64
            }
            
        except Exception as e:
            logger.error("Error encrypting secrets", error=str(e))
            raise
    
    def decrypt_secrets(self, encrypted_secrets: Dict[str, Any]) -> Dict[str, str]:
        """Decrypt a dictionary of secrets"""
        try:
            if not encrypted_secrets or not encrypted_secrets.get("encrypted"):
                return encrypted_secrets or {}
            
            # Decode from base64
            encrypted_data = base64.b64decode(encrypted_secrets["data"].encode())
            
            # Decrypt
            decrypted_data = self.cipher.decrypt(encrypted_data)
            
            # Parse JSON
            secrets = json.loads(decrypted_data.decode())
            
            return secrets
            
        except Exception as e:
            logger.error("Error decrypting secrets", error=str(e))
            # Return empty dict on decryption failure
            return {}
    
    def parse_env_text(self, env_text: str) -> Dict[str, str]:
        """Parse environment variables from text format"""
        try:
            secrets = {}
            
            for line in env_text.strip().split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    secrets[key] = value
            
            return secrets
            
        except Exception as e:
            logger.error("Error parsing environment text", error=str(e))
            raise
    
    def format_env_text(self, secrets: Dict[str, str]) -> str:
        """Format secrets as environment variables text"""
        try:
            lines = []
            for key, value in secrets.items():
                # Escape values with spaces or special characters
                if ' ' in value or '"' in value or "'" in value:
                    value = f'"{value.replace('"', '\\"')}"'
                lines.append(f"{key}={value}")
            
            return '\n'.join(lines)
            
        except Exception as e:
            logger.error("Error formatting environment text", error=str(e))
            raise


# Global instance
secrets_manager = SecretsManager()

# Convenience functions
def encrypt_secrets(secrets: Dict[str, str]) -> Dict[str, Any]:
    """Encrypt secrets"""
    return secrets_manager.encrypt_secrets(secrets)

def decrypt_secrets(encrypted_secrets: Dict[str, Any]) -> Dict[str, str]:
    """Decrypt secrets"""
    return secrets_manager.decrypt_secrets(encrypted_secrets)

def parse_env_text(env_text: str) -> Dict[str, str]:
    """Parse environment variables from text"""
    return secrets_manager.parse_env_text(env_text)

def format_env_text(secrets: Dict[str, str]) -> str:
    """Format secrets as environment text"""
    return secrets_manager.format_env_text(secrets)

