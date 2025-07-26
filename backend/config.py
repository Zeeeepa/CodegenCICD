"""
Configuration management for CodegenCICD Dashboard
"""
import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    app_name: str = "CodegenCICD Dashboard"
    version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database
    database_url: str = Field(env="DATABASE_URL")
    redis_url: str = Field(env="REDIS_URL")
    
    # Security
    secret_encryption_key: str = Field(env="SECRET_ENCRYPTION_KEY")
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=30, env="JWT_EXPIRE_MINUTES")
    
    # External APIs
    codegen_org_id: int = Field(env="CODEGEN_ORG_ID")
    codegen_api_token: str = Field(env="CODEGEN_API_TOKEN")
    github_token: str = Field(env="GITHUB_TOKEN")
    gemini_api_key: str = Field(env="GEMINI_API_KEY")
    
    # Cloudflare
    cloudflare_api_key: str = Field(env="CLOUDFLARE_API_KEY")
    cloudflare_account_id: str = Field(env="CLOUDFLARE_ACCOUNT_ID")
    cloudflare_worker_name: str = Field(env="CLOUDFLARE_WORKER_NAME")
    cloudflare_worker_url: str = Field(env="CLOUDFLARE_WORKER_URL")
    
    # Validation Tools
    grainchain_enabled: bool = Field(default=True, env="GRAINCHAIN_ENABLED")
    grainchain_api_url: str = Field(default="http://localhost:8001", env="GRAINCHAIN_API_URL")
    
    graph_sitter_enabled: bool = Field(default=True, env="GRAPH_SITTER_ENABLED")
    graph_sitter_api_url: str = Field(default="http://localhost:8002", env="GRAPH_SITTER_API_URL")
    
    web_eval_agent_enabled: bool = Field(default=True, env="WEB_EVAL_AGENT_ENABLED")
    web_eval_agent_api_url: str = Field(default="http://localhost:8003", env="WEB_EVAL_AGENT_API_URL")
    
    # WebSocket
    websocket_max_connections: int = Field(default=100, env="WEBSOCKET_MAX_CONNECTIONS")
    websocket_heartbeat_interval: int = Field(default=30, env="WEBSOCKET_HEARTBEAT_INTERVAL")
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_burst: int = Field(default=10, env="RATE_LIMIT_BURST")
    
    # Monitoring
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")
    
    # Background Tasks
    celery_broker_url: str = Field(env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(env="CELERY_RESULT_BACKEND")
    
    # CORS
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://localhost:3000",
        "https://localhost:8000"
    ]
    
    @validator("secret_encryption_key")
    def validate_encryption_key(cls, v):
        if not v:
            raise ValueError("SECRET_ENCRYPTION_KEY must be set")
        return v
    
    @validator("database_url")
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("DATABASE_URL must be set")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings

