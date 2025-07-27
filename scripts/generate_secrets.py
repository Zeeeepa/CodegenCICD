#!/usr/bin/env python3
"""
CodegenCICD - Secret Generation Script
Generates secure secrets for environment configuration
"""
import secrets
import string
import base64
import os
from pathlib import Path


def generate_secret_key(length: int = 32) -> str:
    """Generate a URL-safe secret key"""
    return secrets.token_urlsafe(length)


def generate_password(length: int = 16) -> str:
    """Generate a secure password with mixed characters"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_encryption_key() -> str:
    """Generate a base64-encoded encryption key"""
    key = secrets.token_bytes(32)  # 256-bit key
    return base64.urlsafe_b64encode(key).decode('utf-8')


def generate_salt(length: int = 16) -> str:
    """Generate a salt for encryption"""
    return secrets.token_hex(length)


def main():
    """Generate all required secrets and display them"""
    print("=" * 70)
    print("CodegenCICD - Secret Generation")
    print("=" * 70)
    print()
    
    secrets_data = {
        "SECRET_KEY": generate_secret_key(32),
        "JWT_SECRET_KEY": generate_secret_key(32),
        "ENCRYPTION_KEY": generate_encryption_key(),
        "ENCRYPTION_SALT": generate_salt(16),
        "POSTGRES_PASSWORD": generate_password(20),
        "REDIS_PASSWORD": generate_password(16),
        "GRAFANA_PASSWORD": generate_password(12),
    }
    
    print("Generated Secrets:")
    print("-" * 50)
    for key, value in secrets_data.items():
        print(f"{key}={value}")
    
    print()
    print("=" * 70)
    print("IMPORTANT SECURITY NOTES:")
    print("=" * 70)
    print("1. Store these secrets securely (password manager, vault, etc.)")
    print("2. Never commit these secrets to version control")
    print("3. Use different secrets for each environment")
    print("4. Rotate secrets regularly")
    print("5. Restrict access to these secrets")
    print()
    
    # Optionally write to .env file
    env_file = Path(".env")
    if not env_file.exists():
        response = input("Create .env file with these secrets? (y/N): ")
        if response.lower() == 'y':
            create_env_file(secrets_data)
    else:
        print(f"⚠️  .env file already exists. Please update manually.")
    
    print()
    print("✅ Secret generation completed!")


def create_env_file(secrets_data: dict):
    """Create .env file with generated secrets"""
    template_file = Path(".env.template")
    env_file = Path(".env")
    
    if template_file.exists():
        # Read template and replace placeholders
        with open(template_file, 'r') as f:
            content = f.read()
        
        # Replace secret placeholders
        replacements = {
            "your_secret_key_here_32_chars_minimum": secrets_data["SECRET_KEY"],
            "your_jwt_secret_key_here_32_chars_minimum": secrets_data["JWT_SECRET_KEY"],
            "your_encryption_key_here_32_chars_minimum": secrets_data["ENCRYPTION_KEY"],
            "your_encryption_salt_here_16_chars_minimum": secrets_data["ENCRYPTION_SALT"],
            "your_secure_postgres_password_here": secrets_data["POSTGRES_PASSWORD"],
            "admin": secrets_data["GRAFANA_PASSWORD"],
        }
        
        for placeholder, secret in replacements.items():
            content = content.replace(placeholder, secret)
        
        # Write .env file
        with open(env_file, 'w') as f:
            f.write(content)
        
        print(f"✅ Created .env file with generated secrets")
        print(f"📝 Please review and update API keys in {env_file}")
    else:
        # Create basic .env file
        with open(env_file, 'w') as f:
            f.write("# CodegenCICD Environment Configuration\n")
            f.write("# Generated secrets - DO NOT COMMIT TO VERSION CONTROL\n\n")
            for key, value in secrets_data.items():
                f.write(f"{key}={value}\n")
        
        print(f"✅ Created basic .env file: {env_file}")


if __name__ == "__main__":
    main()

