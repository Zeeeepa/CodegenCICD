"""
Configuration Validators

This module provides comprehensive validation functions for configuration
values with custom validation rules and error reporting.
"""

import re
import socket
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime
import ipaddress

from config.settings import Environment


class ValidationError(Exception):
    """Configuration validation error"""
    
    def __init__(self, field: str, value: Any, message: str):
        self.field = field
        self.value = value
        self.message = message
        super().__init__(f"Validation error for '{field}': {message}")


class ConfigValidators:
    """Collection of configuration validators"""
    
    @staticmethod
    def validate_url(value: str, schemes: Optional[List[str]] = None) -> bool:
        """Validate URL format"""
        if not value:
            return False
            
        try:
            parsed = urllib.parse.urlparse(value)
            
            # Check scheme
            if schemes and parsed.scheme not in schemes:
                return False
                
            # Check if hostname is present
            if not parsed.netloc:
                return False
                
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def validate_email(value: str) -> bool:
        """Validate email format"""
        if not value:
            return False
            
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, value))
    
    @staticmethod
    def validate_ip_address(value: str) -> bool:
        """Validate IP address (IPv4 or IPv6)"""
        if not value:
            return False
            
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_port(value: int) -> bool:
        """Validate port number"""
        return isinstance(value, int) and 1 <= value <= 65535
    
    @staticmethod
    def validate_file_path(value: str, must_exist: bool = False) -> bool:
        """Validate file path"""
        if not value:
            return False
            
        try:
            path = Path(value)
            
            if must_exist:
                return path.exists() and path.is_file()
            else:
                # Check if path is valid (parent directory exists or can be created)
                return True  # Path validation is complex, assume valid for now
                
        except Exception:
            return False
    
    @staticmethod
    def validate_directory_path(value: str, must_exist: bool = False) -> bool:
        """Validate directory path"""
        if not value:
            return False
            
        try:
            path = Path(value)
            
            if must_exist:
                return path.exists() and path.is_dir()
            else:
                return True  # Assume valid for now
                
        except Exception:
            return False
    
    @staticmethod
    def validate_regex(value: str) -> bool:
        """Validate regex pattern"""
        if not value:
            return False
            
        try:
            re.compile(value)
            return True
        except re.error:
            return False
    
    @staticmethod
    def validate_json_string(value: str) -> bool:
        """Validate JSON string"""
        if not value:
            return False
            
        try:
            import json
            json.loads(value)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    
    @staticmethod
    def validate_api_token(value: str, prefix: str) -> bool:
        """Validate API token format"""
        if not value or not prefix:
            return False
            
        return value.startswith(prefix) and len(value) > len(prefix) + 10
    
    @staticmethod
    def validate_github_token(value: str) -> bool:
        """Validate GitHub token format"""
        if not value:
            return False
            
        # GitHub tokens can start with ghp_, github_pat_, or gho_
        valid_prefixes = ['ghp_', 'github_pat_', 'gho_']
        return any(value.startswith(prefix) for prefix in valid_prefixes)
    
    @staticmethod
    def validate_docker_image(value: str) -> bool:
        """Validate Docker image name"""
        if not value:
            return False
            
        # Basic Docker image name validation
        pattern = r'^[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*(?::[a-zA-Z0-9._-]+)?$'
        return bool(re.match(pattern, value))
    
    @staticmethod
    def validate_memory_size(value: str) -> bool:
        """Validate memory size format (e.g., 1g, 512m)"""
        if not value:
            return False
            
        pattern = r'^\d+[kmgtKMGT]?[bB]?$'
        return bool(re.match(pattern, value))
    
    @staticmethod
    def validate_duration(value: str) -> bool:
        """Validate duration format (e.g., 30s, 5m, 1h)"""
        if not value:
            return False
            
        pattern = r'^\d+[smhd]$'
        return bool(re.match(pattern, value))
    
    @staticmethod
    def validate_log_level(value: str) -> bool:
        """Validate log level"""
        if not value:
            return False
            
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        return value.upper() in valid_levels
    
    @staticmethod
    def validate_environment(value: str) -> bool:
        """Validate environment name"""
        if not value:
            return False
            
        try:
            Environment(value.lower())
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_cors_origin(value: str) -> bool:
        """Validate CORS origin"""
        if not value:
            return False
            
        # Allow wildcard
        if value == '*':
            return True
            
        # Validate as URL
        return ConfigValidators.validate_url(value, schemes=['http', 'https'])
    
    @staticmethod
    def validate_webhook_secret(value: str) -> bool:
        """Validate webhook secret"""
        if not value:
            return False
            
        # Webhook secret should be at least 16 characters
        return len(value) >= 16
    
    @staticmethod
    def validate_connection_string(value: str) -> bool:
        """Validate database connection string"""
        if not value:
            return False
            
        # Basic validation - should contain protocol
        return '://' in value or value.endswith('.db') or value == ':memory:'


class ValidationRule:
    """Represents a validation rule for a configuration field"""
    
    def __init__(
        self,
        field_path: str,
        validator: Callable[[Any], bool],
        error_message: str,
        required: bool = True,
        environment_specific: Optional[List[Environment]] = None
    ):
        self.field_path = field_path
        self.validator = validator
        self.error_message = error_message
        self.required = required
        self.environment_specific = environment_specific or []
    
    def applies_to_environment(self, environment: Environment) -> bool:
        """Check if this rule applies to the given environment"""
        if not self.environment_specific:
            return True
        return environment in self.environment_specific
    
    def validate(self, config: Dict[str, Any], environment: Environment) -> Optional[ValidationError]:
        """Validate the field against this rule"""
        if not self.applies_to_environment(environment):
            return None
        
        # Get field value
        value = self._get_nested_value(config, self.field_path)
        
        # Check if field is required
        if self.required and (value is None or value == ""):
            return ValidationError(
                self.field_path,
                value,
                f"Required field is missing or empty"
            )
        
        # Skip validation if field is not required and empty
        if not self.required and (value is None or value == ""):
            return None
        
        # Run validator
        try:
            if not self.validator(value):
                return ValidationError(
                    self.field_path,
                    value,
                    self.error_message
                )
        except Exception as e:
            return ValidationError(
                self.field_path,
                value,
                f"Validation error: {str(e)}"
            )
        
        return None
    
    def _get_nested_value(self, config: Dict[str, Any], field_path: str) -> Any:
        """Get nested value from config dict"""
        parts = field_path.split('.')
        current = config
        
        try:
            for part in parts:
                current = current[part]
            return current
        except (KeyError, TypeError):
            return None


class ConfigurationValidator:
    """Main configuration validator with predefined rules"""
    
    def __init__(self):
        self.rules: List[ValidationRule] = []
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default validation rules"""
        
        # Codegen API validation
        self.add_rule(
            'codegen.api_token',
            lambda v: ConfigValidators.validate_api_token(v, 'sk-'),
            'Codegen API token must start with sk- and be at least 20 characters long'
        )
        
        self.add_rule(
            'codegen.org_id',
            lambda v: v.isdigit() if isinstance(v, str) else isinstance(v, int),
            'Organization ID must be numeric'
        )
        
        self.add_rule(
            'codegen.base_url',
            lambda v: ConfigValidators.validate_url(v, schemes=['https']),
            'Codegen base URL must be a valid HTTPS URL'
        )
        
        # GitHub API validation
        self.add_rule(
            'github.token',
            ConfigValidators.validate_github_token,
            'GitHub token must start with ghp_, github_pat_, or gho_'
        )
        
        self.add_rule(
            'github.base_url',
            lambda v: ConfigValidators.validate_url(v, schemes=['https']),
            'GitHub base URL must be a valid HTTPS URL'
        )
        
        # Cloudflare validation
        self.add_rule(
            'cloudflare.api_key',
            lambda v: len(v) >= 32 if isinstance(v, str) else False,
            'Cloudflare API key must be at least 32 characters long'
        )
        
        self.add_rule(
            'cloudflare.account_id',
            lambda v: len(v) == 32 if isinstance(v, str) else False,
            'Cloudflare account ID must be exactly 32 characters long'
        )
        
        self.add_rule(
            'cloudflare.worker_url',
            lambda v: ConfigValidators.validate_url(v, schemes=['https']),
            'Cloudflare worker URL must be a valid HTTPS URL'
        )
        
        # Gemini API validation
        self.add_rule(
            'gemini.api_key',
            lambda v: ConfigValidators.validate_api_token(v, 'AIzaSy'),
            'Gemini API key must start with AIzaSy'
        )
        
        # Security validation
        self.add_rule(
            'security.secret_key',
            lambda v: len(v) >= 32 if isinstance(v, str) else False,
            'Secret key must be at least 32 characters long'
        )
        
        self.add_rule(
            'security.secret_key',
            lambda v: len(v) >= 64 if isinstance(v, str) else False,
            'Production secret key must be at least 64 characters long',
            environment_specific=[Environment.PRODUCTION]
        )
        
        self.add_rule(
            'security.webhook_secret',
            ConfigValidators.validate_webhook_secret,
            'Webhook secret must be at least 16 characters long',
            required=False
        )
        
        # Server validation
        self.add_rule(
            'server.host',
            lambda v: ConfigValidators.validate_ip_address(v) or v in ['localhost', '0.0.0.0'],
            'Server host must be a valid IP address or localhost'
        )
        
        self.add_rule(
            'server.port',
            ConfigValidators.validate_port,
            'Server port must be between 1 and 65535'
        )
        
        # Database validation
        self.add_rule(
            'database.database_path',
            lambda v: ConfigValidators.validate_file_path(v) or v == ':memory:',
            'Database path must be a valid file path or :memory:'
        )
        
        # Logging validation
        self.add_rule(
            'logging.level',
            lambda v: ConfigValidators.validate_log_level(str(v)),
            'Log level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL'
        )
        
        self.add_rule(
            'logging.log_file',
            ConfigValidators.validate_file_path,
            'Log file path must be valid',
            required=False
        )
        
        # Web-Eval-Agent validation
        self.add_rule(
            'web_eval_agent.browser',
            lambda v: v in ['chromium', 'firefox', 'webkit'],
            'Browser must be chromium, firefox, or webkit'
        )
        
        # Grainchain validation
        self.add_rule(
            'grainchain.base_image',
            ConfigValidators.validate_docker_image,
            'Base image must be a valid Docker image name'
        )
        
        self.add_rule(
            'grainchain.memory_limit',
            ConfigValidators.validate_memory_size,
            'Memory limit must be in format like 1g, 512m, etc.'
        )
    
    def add_rule(
        self,
        field_path: str,
        validator: Callable[[Any], bool],
        error_message: str,
        required: bool = True,
        environment_specific: Optional[List[Environment]] = None
    ):
        """Add a validation rule"""
        rule = ValidationRule(
            field_path,
            validator,
            error_message,
            required,
            environment_specific
        )
        self.rules.append(rule)
    
    def validate(self, config: Dict[str, Any], environment: Environment) -> List[ValidationError]:
        """Validate configuration against all rules"""
        errors = []
        
        for rule in self.rules:
            error = rule.validate(config, environment)
            if error:
                errors.append(error)
        
        return errors
    
    def validate_settings(self, settings) -> List[ValidationError]:
        """Validate Settings object"""
        config_dict = settings.dict()
        return self.validate(config_dict, settings.environment)
    
    def get_validation_summary(self, config: Dict[str, Any], environment: Environment) -> Dict[str, Any]:
        """Get validation summary"""
        errors = self.validate(config, environment)
        
        return {
            'valid': len(errors) == 0,
            'error_count': len(errors),
            'errors': [
                {
                    'field': error.field,
                    'value': str(error.value) if error.value is not None else None,
                    'message': error.message
                }
                for error in errors
            ],
            'validated_at': datetime.now().isoformat(),
            'environment': environment.value
        }


# Global validator instance
_validator: Optional[ConfigurationValidator] = None


def get_validator() -> ConfigurationValidator:
    """Get or create the global validator instance"""
    global _validator
    
    if _validator is None:
        _validator = ConfigurationValidator()
        
    return _validator


def validate_settings(settings) -> List[ValidationError]:
    """Validate settings using the global validator"""
    return get_validator().validate_settings(settings)


def validate_config_dict(config: Dict[str, Any], environment: Environment) -> List[ValidationError]:
    """Validate config dictionary using the global validator"""
    return get_validator().validate(config, environment)

