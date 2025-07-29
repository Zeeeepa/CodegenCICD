"""
Codegen API client configuration
"""
import os
import logging
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ClientConfig:
    """Configuration for the Codegen client"""

    # Core settings
    api_token: str = field(default_factory=lambda: os.getenv("CODEGEN_API_TOKEN", ""))
    org_id: str = field(default_factory=lambda: os.getenv("CODEGEN_ORG_ID", ""))
    base_url: str = field(
        default_factory=lambda: os.getenv(
            "CODEGEN_BASE_URL", "https://api.codegen.com/v1"
        )
    )

    # Performance settings
    timeout: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_TIMEOUT", "30"))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_MAX_RETRIES", "3"))
    )
    retry_delay: float = field(
        default_factory=lambda: float(os.getenv("CODEGEN_RETRY_DELAY", "1.0"))
    )
    retry_backoff_factor: float = field(
        default_factory=lambda: float(os.getenv("CODEGEN_RETRY_BACKOFF", "2.0"))
    )

    # Rate limiting
    rate_limit_requests_per_period: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_RATE_LIMIT_REQUESTS", "60"))
    )
    rate_limit_period_seconds: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_RATE_LIMIT_PERIOD", "60"))
    )
    rate_limit_buffer: float = 0.1

    # Caching
    enable_caching: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_ENABLE_CACHING", "true").lower()
        == "true"
    )
    cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_CACHE_TTL", "300"))
    )
    cache_max_size: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_CACHE_MAX_SIZE", "128"))
    )

    # Features
    enable_webhooks: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_ENABLE_WEBHOOKS", "true").lower()
        == "true"
    )
    enable_bulk_operations: bool = field(
        default_factory=lambda: os.getenv(
            "CODEGEN_ENABLE_BULK_OPERATIONS", "true"
        ).lower()
        == "true"
    )
    enable_streaming: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_ENABLE_STREAMING", "true").lower()
        == "true"
    )
    enable_metrics: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_ENABLE_METRICS", "true").lower()
        == "true"
    )

    # Bulk operations
    bulk_max_workers: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_BULK_MAX_WORKERS", "5"))
    )
    bulk_batch_size: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_BULK_BATCH_SIZE", "100"))
    )

    # Logging
    log_level: str = field(
        default_factory=lambda: os.getenv("CODEGEN_LOG_LEVEL", "INFO")
    )
    log_requests: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_LOG_REQUESTS", "true").lower()
        == "true"
    )
    log_responses: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_LOG_RESPONSES", "false").lower()
        == "true"
    )
    log_request_bodies: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_LOG_REQUEST_BODIES", "false").lower()
        == "true"
    )

    # Webhook settings
    webhook_secret: Optional[str] = field(
        default_factory=lambda: os.getenv("CODEGEN_WEBHOOK_SECRET")
    )

    # User agent
    user_agent: str = field(default_factory=lambda: "codegen-python-client/2.0.0")

    def __post_init__(self):
        if not self.api_token:
            raise ValueError(
                "API token is required. Set CODEGEN_API_TOKEN environment variable or provide it directly."
            )

        # Set up logging
        logging.basicConfig(level=getattr(logging, self.log_level.upper()))


class ConfigPresets:
    """Predefined configuration presets"""

    @staticmethod
    def development() -> ClientConfig:
        """Development configuration with verbose logging and lower limits"""
        return ClientConfig(
            timeout=60,
            max_retries=1,
            rate_limit_requests_per_period=30,
            cache_ttl_seconds=60,
            log_level="DEBUG",
            log_requests=True,
            log_responses=True,
            log_request_bodies=True,
        )

    @staticmethod
    def production() -> ClientConfig:
        """Production configuration with optimized settings"""
        return ClientConfig(
            timeout=30,
            max_retries=3,
            rate_limit_requests_per_period=100,
            cache_ttl_seconds=300,
            log_level="INFO",
            log_requests=True,
            log_responses=False,
            log_request_bodies=False,
        )

    @staticmethod
    def high_performance() -> ClientConfig:
        """High performance configuration for heavy workloads"""
        return ClientConfig(
            timeout=45,
            max_retries=5,
            rate_limit_requests_per_period=200,
            cache_ttl_seconds=600,
            cache_max_size=256,
            bulk_max_workers=10,
            bulk_batch_size=200,
            log_level="WARNING",
        )

    @staticmethod
    def testing() -> ClientConfig:
        """Testing configuration with minimal caching and retries"""
        return ClientConfig(
            timeout=10,
            max_retries=1,
            enable_caching=False,
            rate_limit_requests_per_period=10,
            log_level="DEBUG",
        )

