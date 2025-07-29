"""
Application Settings and Configuration

This module defines all application settings with proper validation,
environment variable support, and configuration management.
"""

import os
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from pydantic import BaseSettings, Field, validator, root_validator
from enum import Enum


class Environment(str, Enum):
    """Application environment types"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseSettings(BaseSettings):
    """Database configuration settings"""
    
    # Database connection
    database_path: str = Field(default="data/codegen_cicd.db", description="SQLite database file path")
    max_connections: int = Field(default=10, ge=1, le=100, description="Maximum database connections")
    connection_timeout: float = Field(default=30.0, ge=1.0, description="Connection timeout in seconds")
    
    # Performance settings
    enable_wal_mode: bool = Field(default=True, description="Enable WAL mode for better concurrency")
    enable_foreign_keys: bool = Field(default=True, description="Enable foreign key constraints")
    busy_timeout: int = Field(default=30000, ge=1000, description="Busy timeout in milliseconds")
    cache_size: int = Field(default=-64000, description="Cache size (-64MB)")
    
    # Migration settings
    migrations_dir: str = Field(default="database/migrations", description="Migrations directory")
    auto_migrate: bool = Field(default=True, description="Automatically run migrations on startup")
    
    class Config:
        env_prefix = "DB_"


class CodegenSettings(BaseSettings):
    """Codegen API configuration"""
    
    api_token: str = Field(..., description="Codegen API token")
    org_id: str = Field(..., description="Codegen organization ID")
    base_url: str = Field(default="https://api.codegen.com/v1", description="Codegen API base URL")
    
    # Performance settings
    timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, ge=0.1, description="Retry delay in seconds")
    
    # Rate limiting
    rate_limit_requests: int = Field(default=60, ge=1, description="Requests per minute")
    rate_limit_period: int = Field(default=60, ge=1, description="Rate limit period in seconds")
    
    # Features
    enable_caching: bool = Field(default=True, description="Enable response caching")
    cache_ttl: int = Field(default=300, ge=60, description="Cache TTL in seconds")
    
    @validator('api_token')
    def validate_api_token(cls, v):
        if not v.startswith('sk-'):
            raise ValueError('Codegen API token must start with sk-')
        return v
    
    @validator('org_id')
    def validate_org_id(cls, v):
        if not v.isdigit():
            raise ValueError('Organization ID must be numeric')
        return v
    
    class Config:
        env_prefix = "CODEGEN_"


class GitHubSettings(BaseSettings):
    """GitHub API configuration"""
    
    token: str = Field(..., description="GitHub personal access token")
    base_url: str = Field(default="https://api.github.com", description="GitHub API base URL")
    
    # Performance settings
    timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    
    # Rate limiting
    rate_limit_requests: int = Field(default=5000, ge=100, description="Requests per hour")
    rate_limit_buffer: float = Field(default=0.1, ge=0.0, le=0.5, description="Rate limit buffer")
    
    # Features
    enable_caching: bool = Field(default=True, description="Enable response caching")
    cache_ttl: int = Field(default=300, ge=60, description="Cache TTL in seconds")
    
    @validator('token')
    def validate_github_token(cls, v):
        if not (v.startswith('ghp_') or v.startswith('github_pat_')):
            raise ValueError('GitHub token must start with ghp_ or github_pat_')
        return v
    
    class Config:
        env_prefix = "GITHUB_"


class CloudflareSettings(BaseSettings):
    """Cloudflare API configuration"""
    
    api_key: str = Field(..., description="Cloudflare API key")
    account_id: str = Field(..., description="Cloudflare account ID")
    worker_name: str = Field(default="webhook-gateway", description="Cloudflare worker name")
    worker_url: str = Field(..., description="Cloudflare worker URL")
    
    # Performance settings
    timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    
    @validator('worker_url')
    def validate_worker_url(cls, v):
        if not v.startswith('https://'):
            raise ValueError('Worker URL must use HTTPS')
        return v
    
    class Config:
        env_prefix = "CLOUDFLARE_"


class GeminiSettings(BaseSettings):
    """Google Gemini API configuration"""
    
    api_key: str = Field(..., description="Google Gemini API key")
    model: str = Field(default="gemini-pro", description="Gemini model to use")
    base_url: str = Field(default="https://generativelanguage.googleapis.com", description="Gemini API base URL")
    
    # Performance settings
    timeout: int = Field(default=60, ge=10, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    
    # Generation settings
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Generation temperature")
    max_tokens: int = Field(default=2048, ge=1, le=8192, description="Maximum tokens to generate")
    
    @validator('api_key')
    def validate_gemini_api_key(cls, v):
        if not v.startswith('AIzaSy'):
            raise ValueError('Gemini API key must start with AIzaSy')
        return v
    
    class Config:
        env_prefix = "GEMINI_"


class WebEvalAgentSettings(BaseSettings):
    """Web-Eval-Agent configuration"""
    
    # Browser settings
    browser: str = Field(default="chromium", description="Browser to use for testing")
    headless: bool = Field(default=True, description="Run browser in headless mode")
    viewport_width: int = Field(default=1920, ge=800, description="Browser viewport width")
    viewport_height: int = Field(default=1080, ge=600, description="Browser viewport height")
    
    # Test settings
    default_timeout: int = Field(default=30000, ge=5000, description="Default timeout in milliseconds")
    screenshot_on_failure: bool = Field(default=True, description="Take screenshot on test failure")
    video_recording: bool = Field(default=False, description="Enable video recording")
    
    # Paths
    screenshots_dir: str = Field(default="test_results/screenshots", description="Screenshots directory")
    videos_dir: str = Field(default="test_results/videos", description="Videos directory")
    logs_dir: str = Field(default="test_results/logs", description="Logs directory")
    
    class Config:
        env_prefix = "WEB_EVAL_"


class GrainchainSettings(BaseSettings):
    """Grainchain configuration"""
    
    # Docker settings
    docker_host: str = Field(default="unix:///var/run/docker.sock", description="Docker host")
    base_image: str = Field(default="ubuntu:22.04", description="Base Docker image")
    
    # Resource limits
    memory_limit: str = Field(default="2g", description="Memory limit for containers")
    cpu_limit: str = Field(default="2", description="CPU limit for containers")
    disk_limit: str = Field(default="10g", description="Disk limit for containers")
    
    # Timeout settings
    creation_timeout: int = Field(default=300, ge=60, description="Container creation timeout in seconds")
    execution_timeout: int = Field(default=1800, ge=60, description="Command execution timeout in seconds")
    
    # Cleanup settings
    auto_cleanup: bool = Field(default=True, description="Automatically cleanup containers")
    cleanup_delay: int = Field(default=3600, ge=300, description="Cleanup delay in seconds")
    
    class Config:
        env_prefix = "GRAINCHAIN_"


class SecuritySettings(BaseSettings):
    """Security configuration"""
    
    # Encryption
    secret_key: str = Field(..., description="Secret key for encryption")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    token_expire_hours: int = Field(default=24, ge=1, description="Token expiration in hours")
    
    # CORS
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    cors_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"], description="CORS allowed methods")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, ge=1, description="Requests per minute per IP")
    
    # Webhook security
    webhook_secret: Optional[str] = Field(default=None, description="Webhook signature secret")
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters long')
        return v
    
    class Config:
        env_prefix = "SECURITY_"


class LoggingSettings(BaseSettings):
    """Logging configuration"""
    
    level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    
    # File logging
    log_to_file: bool = Field(default=True, description="Enable file logging")
    log_file: str = Field(default="logs/codegen_cicd.log", description="Log file path")
    max_file_size: int = Field(default=10485760, ge=1048576, description="Max log file size in bytes")
    backup_count: int = Field(default=5, ge=1, description="Number of backup log files")
    
    # Console logging
    log_to_console: bool = Field(default=True, description="Enable console logging")
    console_level: LogLevel = Field(default=LogLevel.INFO, description="Console logging level")
    
    # Structured logging
    structured_logging: bool = Field(default=True, description="Enable structured logging")
    include_trace_id: bool = Field(default=True, description="Include trace ID in logs")
    
    class Config:
        env_prefix = "LOG_"


class MonitoringSettings(BaseSettings):
    """Monitoring and metrics configuration"""
    
    # Metrics
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, ge=1024, le=65535, description="Metrics server port")
    
    # Health checks
    health_check_interval: int = Field(default=30, ge=10, description="Health check interval in seconds")
    health_check_timeout: int = Field(default=5, ge=1, description="Health check timeout in seconds")
    
    # Alerting
    enable_alerting: bool = Field(default=False, description="Enable alerting")
    alert_webhook_url: Optional[str] = Field(default=None, description="Alert webhook URL")
    
    class Config:
        env_prefix = "MONITORING_"


class ServerSettings(BaseSettings):
    """Server configuration"""
    
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1024, le=65535, description="Server port")
    workers: int = Field(default=1, ge=1, description="Number of worker processes")
    
    # Performance
    keepalive_timeout: int = Field(default=5, ge=1, description="Keep-alive timeout in seconds")
    max_requests: int = Field(default=1000, ge=1, description="Max requests per worker")
    max_requests_jitter: int = Field(default=100, ge=0, description="Max requests jitter")
    
    # SSL
    ssl_enabled: bool = Field(default=False, description="Enable SSL")
    ssl_cert_file: Optional[str] = Field(default=None, description="SSL certificate file")
    ssl_key_file: Optional[str] = Field(default=None, description="SSL private key file")
    
    class Config:
        env_prefix = "SERVER_"


class Settings(BaseSettings):
    """Main application settings"""
    
    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Application environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    testing: bool = Field(default=False, description="Enable testing mode")
    
    # Application info
    app_name: str = Field(default="CodegenCICD Dashboard", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    app_description: str = Field(
        default="AI-Powered CICD Dashboard with comprehensive testing and validation",
        description="Application description"
    )
    
    # Component settings
    database: DatabaseSettings = DatabaseSettings()
    codegen: CodegenSettings = CodegenSettings()
    github: GitHubSettings = GitHubSettings()
    cloudflare: CloudflareSettings = CloudflareSettings()
    gemini: GeminiSettings = GeminiSettings()
    web_eval_agent: WebEvalAgentSettings = WebEvalAgentSettings()
    grainchain: GrainchainSettings = GrainchainSettings()
    security: SecuritySettings = SecuritySettings()
    logging: LoggingSettings = LoggingSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    server: ServerSettings = ServerSettings()
    
    @root_validator
    def validate_environment_settings(cls, values):
        """Validate settings based on environment"""
        env = values.get('environment')
        
        if env == Environment.PRODUCTION:
            # Production-specific validations
            if values.get('debug', False):
                raise ValueError('Debug mode must be disabled in production')
            
            # Ensure secure settings
            security = values.get('security')
            if security and len(security.secret_key) < 64:
                raise ValueError('Production secret key must be at least 64 characters')
        
        elif env == Environment.DEVELOPMENT:
            # Development-specific settings
            values['debug'] = True
            
        return values
    
    @validator('environment', pre=True)
    def validate_environment(cls, v):
        if isinstance(v, str):
            return Environment(v.lower())
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Custom JSON encoders
        json_encoders = {
            Path: str
        }


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance"""
    global _settings
    
    if _settings is None:
        _settings = Settings()
        
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment"""
    global _settings
    _settings = Settings()
    return _settings


# Environment-specific setting factories
def get_development_settings() -> Settings:
    """Get development settings"""
    os.environ['ENVIRONMENT'] = 'development'
    return Settings()


def get_testing_settings() -> Settings:
    """Get testing settings"""
    os.environ['ENVIRONMENT'] = 'testing'
    return Settings()


def get_production_settings() -> Settings:
    """Get production settings"""
    os.environ['ENVIRONMENT'] = 'production'
    return Settings()

