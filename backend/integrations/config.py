"""
Advanced configuration management for Codegen API client
"""
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class ClientConfig:
    """Comprehensive configuration for Codegen API client"""
    
    # Core API Configuration
    api_token: str = field(
        default_factory=lambda: os.getenv("CODEGEN_API_TOKEN", "")
    )
    base_url: str = field(
        default_factory=lambda: os.getenv("CODEGEN_BASE_URL", "https://api.codegen.com/v1")
    )
    org_id: Optional[str] = field(
        default_factory=lambda: os.getenv("CODEGEN_ORG_ID")
    )
    
    # Timeout Configuration
    timeout: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_TIMEOUT", "30"))
    )
    agent_run_timeout: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_AGENT_RUN_TIMEOUT", "1800"))  # 30 minutes
    )
    
    # Retry Configuration
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_MAX_RETRIES", "3"))
    )
    retry_delay: float = field(
        default_factory=lambda: float(os.getenv("CODEGEN_RETRY_DELAY", "1.0"))
    )
    retry_backoff_factor: float = field(
        default_factory=lambda: float(os.getenv("CODEGEN_RETRY_BACKOFF_FACTOR", "2.0"))
    )
    retry_jitter: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_RETRY_JITTER", "true").lower() == "true"
    )
    
    # Rate Limiting Configuration
    rate_limit_requests_per_period: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_RATE_LIMIT_REQUESTS", "60"))
    )
    rate_limit_period_seconds: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_RATE_LIMIT_PERIOD", "60"))
    )
    rate_limit_buffer: float = field(
        default_factory=lambda: float(os.getenv("CODEGEN_RATE_LIMIT_BUFFER", "0.1"))  # 10% buffer
    )
    
    # Caching Configuration
    enable_caching: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_ENABLE_CACHING", "true").lower() == "true"
    )
    cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_CACHE_TTL", "300"))  # 5 minutes
    )
    cache_max_size: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_CACHE_MAX_SIZE", "128"))
    )
    
    # Logging Configuration
    log_level: str = field(
        default_factory=lambda: os.getenv("CODEGEN_LOG_LEVEL", "INFO")
    )
    log_requests: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_LOG_REQUESTS", "true").lower() == "true"
    )
    log_responses: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_LOG_RESPONSES", "false").lower() == "true"
    )
    log_sensitive_data: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_LOG_SENSITIVE_DATA", "false").lower() == "true"
    )
    
    # Webhook Configuration
    webhook_secret: Optional[str] = field(
        default_factory=lambda: os.getenv("CODEGEN_WEBHOOK_SECRET")
    )
    webhook_timeout: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_WEBHOOK_TIMEOUT", "30"))
    )
    
    # Bulk Operations Configuration
    bulk_max_workers: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_BULK_MAX_WORKERS", "5"))
    )
    bulk_batch_size: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_BULK_BATCH_SIZE", "100"))
    )
    
    # Feature Toggles
    enable_webhooks: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_ENABLE_WEBHOOKS", "true").lower() == "true"
    )
    enable_bulk_operations: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_ENABLE_BULK_OPERATIONS", "true").lower() == "true"
    )
    enable_streaming: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_ENABLE_STREAMING", "true").lower() == "true"
    )
    enable_metrics: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_ENABLE_METRICS", "true").lower() == "true"
    )
    
    # Development/Debug Configuration
    debug_mode: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_DEBUG_MODE", "false").lower() == "true"
    )
    mock_responses: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_MOCK_RESPONSES", "false").lower() == "true"
    )
    
    # Custom Headers
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate_config()
        self._load_custom_headers()
    
    def _validate_config(self):
        """Validate configuration values"""
        if not self.api_token:
            raise ValueError(
                "API token is required. Set CODEGEN_API_TOKEN environment variable or pass api_token parameter."
            )
        
        if not self.base_url:
            raise ValueError("Base URL cannot be empty")
        
        if not self.base_url.startswith(('http://', 'https://')):
            raise ValueError("Base URL must start with http:// or https://")
        
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        
        if self.agent_run_timeout <= 0:
            raise ValueError("Agent run timeout must be positive")
        
        if self.max_retries < 0:
            raise ValueError("Max retries cannot be negative")
        
        if self.retry_delay < 0:
            raise ValueError("Retry delay cannot be negative")
        
        if self.retry_backoff_factor < 1:
            raise ValueError("Retry backoff factor must be >= 1")
        
        if self.rate_limit_requests_per_period <= 0:
            raise ValueError("Rate limit requests per period must be positive")
        
        if self.rate_limit_period_seconds <= 0:
            raise ValueError("Rate limit period must be positive")
        
        if not (0 <= self.rate_limit_buffer <= 1):
            raise ValueError("Rate limit buffer must be between 0 and 1")
        
        if self.cache_ttl_seconds < 0:
            raise ValueError("Cache TTL cannot be negative")
        
        if self.cache_max_size <= 0:
            raise ValueError("Cache max size must be positive")
        
        if self.webhook_timeout <= 0:
            raise ValueError("Webhook timeout must be positive")
        
        if self.bulk_max_workers <= 0:
            raise ValueError("Bulk max workers must be positive")
        
        if self.bulk_batch_size <= 0:
            raise ValueError("Bulk batch size must be positive")
        
        if self.log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ValueError("Log level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    
    def _load_custom_headers(self):
        """Load custom headers from environment variables"""
        # Load headers with CODEGEN_HEADER_ prefix
        for key, value in os.environ.items():
            if key.startswith('CODEGEN_HEADER_'):
                header_name = key[15:].replace('_', '-').lower()  # Remove prefix and convert to header format
                self.custom_headers[header_name] = value
    
    def get_user_agent(self) -> str:
        """Get User-Agent string for requests"""
        return f"CodegenCICD-Enhanced-Client/2.0 (Python)"
    
    def get_default_headers(self) -> Dict[str, str]:
        """Get default headers for API requests"""
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "User-Agent": self.get_user_agent(),
            "Accept": "application/json"
        }
        
        # Add custom headers
        headers.update(self.custom_headers)
        
        return headers
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)"""
        config_dict = {}
        for key, value in self.__dict__.items():
            if key in ['api_token', 'webhook_secret']:
                config_dict[key] = '[REDACTED]' if value else None
            else:
                config_dict[key] = value
        return config_dict
    
    @classmethod
    def from_file(cls, config_path: str) -> 'ClientConfig':
        """Load configuration from file"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Support for different file formats
        if config_file.suffix == '.json':
            import json
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        elif config_file.suffix in ['.yml', '.yaml']:
            try:
                import yaml
                with open(config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
            except ImportError:
                raise ImportError("PyYAML is required to load YAML configuration files")
        else:
            raise ValueError(f"Unsupported configuration file format: {config_file.suffix}")
        
        return cls(**config_data)
    
    def save_to_file(self, config_path: str, exclude_sensitive: bool = True):
        """Save configuration to file"""
        config_file = Path(config_path)
        config_data = self.to_dict() if exclude_sensitive else self.__dict__
        
        # Create directory if it doesn't exist
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        if config_file.suffix == '.json':
            import json
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
        elif config_file.suffix in ['.yml', '.yaml']:
            try:
                import yaml
                with open(config_file, 'w') as f:
                    yaml.dump(config_data, f, default_flow_style=False)
            except ImportError:
                raise ImportError("PyYAML is required to save YAML configuration files")
        else:
            raise ValueError(f"Unsupported configuration file format: {config_file.suffix}")
    
    def update(self, **kwargs):
        """Update configuration with new values"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"Unknown configuration parameter: {key}")
        
        # Re-validate after update
        self._validate_config()
    
    def copy(self) -> 'ClientConfig':
        """Create a copy of the configuration"""
        return ClientConfig(**self.__dict__)


# Predefined configurations for common use cases
class ConfigPresets:
    """Predefined configuration presets"""
    
    @staticmethod
    def development() -> ClientConfig:
        """Configuration optimized for development"""
        return ClientConfig(
            debug_mode=True,
            log_level="DEBUG",
            log_requests=True,
            log_responses=True,
            timeout=60,
            max_retries=1,
            enable_caching=False,
            rate_limit_requests_per_period=30,  # Lower rate limit for dev
        )
    
    @staticmethod
    def production() -> ClientConfig:
        """Configuration optimized for production"""
        return ClientConfig(
            debug_mode=False,
            log_level="INFO",
            log_requests=True,
            log_responses=False,
            log_sensitive_data=False,
            timeout=30,
            max_retries=3,
            enable_caching=True,
            cache_ttl_seconds=300,
            rate_limit_requests_per_period=60,
        )
    
    @staticmethod
    def high_performance() -> ClientConfig:
        """Configuration optimized for high performance"""
        return ClientConfig(
            debug_mode=False,
            log_level="WARNING",
            log_requests=False,
            log_responses=False,
            timeout=15,
            max_retries=2,
            enable_caching=True,
            cache_ttl_seconds=600,  # Longer cache
            bulk_max_workers=10,  # More concurrent workers
            rate_limit_requests_per_period=100,  # Higher rate limit
        )
    
    @staticmethod
    def testing() -> ClientConfig:
        """Configuration optimized for testing"""
        return ClientConfig(
            debug_mode=True,
            log_level="DEBUG",
            timeout=5,
            max_retries=0,  # No retries in tests
            enable_caching=False,
            mock_responses=True,
            rate_limit_requests_per_period=1000,  # No rate limiting in tests
        )


def load_config_from_env() -> ClientConfig:
    """Load configuration from environment variables"""
    return ClientConfig()


def get_config_for_environment(env: str = None) -> ClientConfig:
    """Get configuration based on environment"""
    env = env or os.getenv('ENVIRONMENT', 'development').lower()
    
    if env == 'production':
        return ConfigPresets.production()
    elif env == 'testing':
        return ConfigPresets.testing()
    elif env == 'high_performance':
        return ConfigPresets.high_performance()
    else:
        return ConfigPresets.development()

