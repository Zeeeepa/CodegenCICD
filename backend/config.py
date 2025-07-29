"""
Unified Configuration Management for CodegenCICD Dashboard
Supports tiered configuration: basic -> intermediate -> advanced
"""
import os
from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from enum import Enum


class ConfigurationTier(str, Enum):
    """Configuration complexity tiers"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Settings(BaseSettings):
    """Unified application settings with tiered configuration support"""
    
    # =============================================================================
    # CORE APPLICATION SETTINGS
    # =============================================================================
    app_name: str = "CodegenCICD Dashboard"
    version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    config_tier: ConfigurationTier = Field(default=ConfigurationTier.BASIC, env="CONFIG_TIER")
    
    # =============================================================================
    # DATABASE CONFIGURATION
    # =============================================================================
    postgres_password: str = Field(env="POSTGRES_PASSWORD")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/codegencd",
        env="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # =============================================================================
    # SECURITY CONFIGURATION
    # =============================================================================
    secret_key: str = Field(env="SECRET_KEY")
    encryption_key: str = Field(env="ENCRYPTION_KEY")
    encryption_salt: str = Field(env="ENCRYPTION_SALT")
    jwt_secret_key: Optional[str] = Field(default=None, env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=30, env="JWT_EXPIRE_MINUTES")
    
    # =============================================================================
    # CODEGEN API CONFIGURATION
    # =============================================================================
    codegen_org_id: int = Field(env="CODEGEN_ORG_ID")
    codegen_api_token: str = Field(env="CODEGEN_API_TOKEN")
    
    # =============================================================================
    # GITHUB INTEGRATION
    # =============================================================================
    github_token: str = Field(env="GITHUB_TOKEN")
    github_webhook_secret: Optional[str] = Field(default=None, env="GITHUB_WEBHOOK_SECRET")
    
    # =============================================================================
    # AI SERVICES
    # =============================================================================
    gemini_api_key: str = Field(env="GEMINI_API_KEY")
    
    # =============================================================================
    # CLOUDFLARE CONFIGURATION
    # =============================================================================
    cloudflare_api_key: str = Field(env="CLOUDFLARE_API_KEY")
    cloudflare_account_id: str = Field(env="CLOUDFLARE_ACCOUNT_ID")
    cloudflare_email: str = Field(default="admin@example.com", env="CLOUDFLARE_EMAIL")
    cloudflare_worker_name: str = Field(default="webhook-gateway", env="CLOUDFLARE_WORKER_NAME")
    cloudflare_worker_url: str = Field(env="CLOUDFLARE_WORKER_URL")
    
    # =============================================================================
    # VALIDATION TOOLS CONFIGURATION
    # =============================================================================
    # Grainchain (sandboxing)
    grainchain_enabled: bool = Field(default=True, env="GRAINCHAIN_ENABLED")
    grainchain_url: str = Field(default="http://localhost:8001", env="GRAINCHAIN_URL")
    grainchain_workspace_dir: str = Field(default="/tmp/grainchain_workspaces", env="GRAINCHAIN_WORKSPACE_DIR")
    grainchain_max_instances: int = Field(default=10, env="GRAINCHAIN_MAX_INSTANCES")
    grainchain_instance_timeout: int = Field(default=3600, env="GRAINCHAIN_INSTANCE_TIMEOUT")
    
    # Web-eval-agent (UI testing)
    web_eval_enabled: bool = Field(default=True, env="WEB_EVAL_ENABLED")
    web_eval_browser: str = Field(default="chromium", env="WEB_EVAL_BROWSER")
    web_eval_headless: bool = Field(default=True, env="WEB_EVAL_HEADLESS")
    web_eval_timeout: int = Field(default=30000, env="WEB_EVAL_TIMEOUT")
    web_eval_viewport_width: int = Field(default=1920, env="WEB_EVAL_VIEWPORT_WIDTH")
    web_eval_viewport_height: int = Field(default=1080, env="WEB_EVAL_VIEWPORT_HEIGHT")
    
    # Graph-sitter (code quality)
    graph_sitter_enabled: bool = Field(default=True, env="GRAPH_SITTER_ENABLED")
    graph_sitter_languages: str = Field(default="typescript,javascript,python,rust,go", env="GRAPH_SITTER_LANGUAGES")
    graph_sitter_max_file_size: int = Field(default=1048576, env="GRAPH_SITTER_MAX_FILE_SIZE")
    graph_sitter_analysis_timeout: int = Field(default=60, env="GRAPH_SITTER_ANALYSIS_TIMEOUT")
    
    # =============================================================================
    # ADVANCED CONFIGURATION (Tier: INTERMEDIATE+)
    # =============================================================================
    # WebSocket Configuration
    websocket_max_connections: int = Field(default=100, env="WEBSOCKET_MAX_CONNECTIONS")
    websocket_heartbeat_interval: int = Field(default=30, env="WEBSOCKET_HEARTBEAT_INTERVAL")
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_burst: int = Field(default=10, env="RATE_LIMIT_BURST")
    
    # Background Tasks
    celery_broker_url: Optional[str] = Field(default=None, env="CELERY_BROKER_URL")
    celery_result_backend: Optional[str] = Field(default=None, env="CELERY_RESULT_BACKEND")
    
    # =============================================================================
    # ENTERPRISE CONFIGURATION (Tier: ADVANCED)
    # =============================================================================
    # Monitoring
    prometheus_enabled: bool = Field(default=False, env="PROMETHEUS_ENABLED")
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")
    grafana_password: Optional[str] = Field(default=None, env="GRAFANA_PASSWORD")
    
    # Validation Pipeline
    max_concurrent_validations: int = Field(default=5, env="MAX_CONCURRENT_VALIDATIONS")
    validation_timeout: int = Field(default=1800, env="VALIDATION_TIMEOUT")
    max_validation_retries: int = Field(default=3, env="MAX_VALIDATION_RETRIES")
    retry_delay_seconds: int = Field(default=30, env="RETRY_DELAY_SECONDS")
    
    # SSL Configuration
    ssl_cert_path: Optional[str] = Field(default=None, env="SSL_CERT_PATH")
    ssl_key_path: Optional[str] = Field(default=None, env="SSL_KEY_PATH")
    
    # Email Configuration
    smtp_host: Optional[str] = Field(default=None, env="SMTP_HOST")
    smtp_port: Optional[int] = Field(default=None, env="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, env="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    
    # CORS Configuration
    allowed_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8000",
            "https://localhost:3000",
            "https://localhost:8000"
        ]
    )
    
    @validator("allowed_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("graph_sitter_languages", pre=True)
    def parse_languages(cls, v):
        if isinstance(v, str):
            return v.split(",")
        return v
    
    @validator("encryption_key")
    def validate_encryption_key(cls, v):
        if not v:
            raise ValueError("ENCRYPTION_KEY must be set")
        return v
    
    @validator("database_url")
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("DATABASE_URL must be set")
        return v
    
    def get_active_features(self) -> Dict[str, bool]:
        """Get active features based on configuration tier"""
        features = {
            # Basic features (always active)
            "projects": True,
            "agent_runs": True,
            "basic_validation": True,
            "github_integration": True,
            "codegen_integration": True,
            
            # Intermediate features
            "websocket_updates": self.config_tier in [ConfigurationTier.INTERMEDIATE, ConfigurationTier.ADVANCED],
            "rate_limiting": self.config_tier in [ConfigurationTier.INTERMEDIATE, ConfigurationTier.ADVANCED],
            "background_tasks": self.config_tier in [ConfigurationTier.INTERMEDIATE, ConfigurationTier.ADVANCED],
            "advanced_validation": self.config_tier in [ConfigurationTier.INTERMEDIATE, ConfigurationTier.ADVANCED],
            
            # Advanced features
            "monitoring": self.config_tier == ConfigurationTier.ADVANCED,
            "ssl_support": self.config_tier == ConfigurationTier.ADVANCED,
            "email_notifications": self.config_tier == ConfigurationTier.ADVANCED,
            "enterprise_security": self.config_tier == ConfigurationTier.ADVANCED,
        }
        return features
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a specific feature is enabled"""
        return self.get_active_features().get(feature, False)
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


def get_database_url() -> str:
    """Get database URL with proper formatting"""
    return settings.database_url.replace("postgresql://", "postgresql+asyncpg://")


def get_redis_url() -> str:
    """Get Redis URL"""
    return settings.redis_url


def is_development() -> bool:
    """Check if running in development mode"""
    return settings.environment == "development"


def is_production() -> bool:
    """Check if running in production mode"""
    return settings.environment == "production"


def get_cors_origins() -> List[str]:
    """Get CORS origins based on environment"""
    if is_development():
        return settings.allowed_origins + [
            "http://localhost:3001",  # Additional dev ports
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000"
        ]
    return settings.allowed_origins
