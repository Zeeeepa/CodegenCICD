"""
Configuration Manager

This module provides advanced configuration management with validation,
hot reloading, environment-specific overrides, and configuration monitoring.
"""

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config.settings import Settings, get_settings, Environment

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Configuration-related error"""
    pass


class ConfigChangeHandler(FileSystemEventHandler):
    """File system event handler for configuration changes"""
    
    def __init__(self, config_manager: 'ConfigManager'):
        self.config_manager = config_manager
        self.last_modified = {}
        
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Only process .env files and config files
        if file_path.suffix not in ['.env', '.json', '.yaml', '.yml']:
            return
            
        # Debounce rapid file changes
        now = time.time()
        last_mod = self.last_modified.get(file_path, 0)
        
        if now - last_mod < 1.0:  # 1 second debounce
            return
            
        self.last_modified[file_path] = now
        
        logger.info(f"Configuration file changed: {file_path}")
        self.config_manager._handle_config_change(file_path)


class ConfigValidator:
    """Configuration validation utilities"""
    
    @staticmethod
    def validate_required_fields(config: Dict[str, Any], required_fields: List[str]) -> List[str]:
        """Validate that required fields are present"""
        missing_fields = []
        
        for field in required_fields:
            if '.' in field:
                # Nested field validation
                parts = field.split('.')
                current = config
                
                try:
                    for part in parts:
                        current = current[part]
                except (KeyError, TypeError):
                    missing_fields.append(field)
            else:
                # Top-level field validation
                if field not in config or config[field] is None:
                    missing_fields.append(field)
                    
        return missing_fields
    
    @staticmethod
    def validate_field_types(config: Dict[str, Any], field_types: Dict[str, type]) -> List[str]:
        """Validate field types"""
        type_errors = []
        
        for field, expected_type in field_types.items():
            if '.' in field:
                # Nested field validation
                parts = field.split('.')
                current = config
                
                try:
                    for part in parts:
                        current = current[part]
                        
                    if not isinstance(current, expected_type):
                        type_errors.append(f"{field}: expected {expected_type.__name__}, got {type(current).__name__}")
                        
                except (KeyError, TypeError):
                    # Field doesn't exist, skip type validation
                    pass
            else:
                # Top-level field validation
                if field in config and config[field] is not None:
                    if not isinstance(config[field], expected_type):
                        type_errors.append(f"{field}: expected {expected_type.__name__}, got {type(config[field]).__name__}")
                        
        return type_errors
    
    @staticmethod
    def validate_field_ranges(config: Dict[str, Any], field_ranges: Dict[str, tuple]) -> List[str]:
        """Validate numeric field ranges"""
        range_errors = []
        
        for field, (min_val, max_val) in field_ranges.items():
            if '.' in field:
                # Nested field validation
                parts = field.split('.')
                current = config
                
                try:
                    for part in parts:
                        current = current[part]
                        
                    if isinstance(current, (int, float)):
                        if current < min_val or current > max_val:
                            range_errors.append(f"{field}: value {current} not in range [{min_val}, {max_val}]")
                            
                except (KeyError, TypeError):
                    # Field doesn't exist, skip range validation
                    pass
            else:
                # Top-level field validation
                if field in config and isinstance(config[field], (int, float)):
                    value = config[field]
                    if value < min_val or value > max_val:
                        range_errors.append(f"{field}: value {value} not in range [{min_val}, {max_val}]")
                        
        return range_errors


class ConfigManager:
    """Advanced configuration manager with hot reloading and validation"""
    
    def __init__(self, watch_files: bool = True):
        self.settings = get_settings()
        self.watch_files = watch_files
        self.observers = []
        self.change_callbacks: List[Callable[[Settings], None]] = []
        self.lock = threading.RLock()
        self.last_reload = datetime.now()
        self.reload_count = 0
        
        # Configuration validation rules
        self.required_fields = [
            'codegen.api_token',
            'codegen.org_id',
            'github.token',
            'cloudflare.api_key',
            'cloudflare.account_id',
            'gemini.api_key',
            'security.secret_key'
        ]
        
        self.field_types = {
            'database.max_connections': int,
            'database.connection_timeout': float,
            'codegen.timeout': int,
            'codegen.max_retries': int,
            'github.timeout': int,
            'server.port': int,
            'server.workers': int
        }
        
        self.field_ranges = {
            'database.max_connections': (1, 100),
            'database.connection_timeout': (1.0, 300.0),
            'codegen.timeout': (5, 300),
            'codegen.max_retries': (0, 10),
            'server.port': (1024, 65535),
            'server.workers': (1, 32)
        }
        
        # Start file watching if enabled
        if self.watch_files:
            self._start_file_watching()
            
        # Validate initial configuration
        self._validate_configuration()
        
        logger.info("Configuration manager initialized")
    
    def _start_file_watching(self):
        """Start watching configuration files for changes"""
        try:
            # Watch .env file
            env_file = Path('.env')
            if env_file.exists():
                observer = Observer()
                handler = ConfigChangeHandler(self)
                observer.schedule(handler, str(env_file.parent), recursive=False)
                observer.start()
                self.observers.append(observer)
                logger.info(f"Watching configuration file: {env_file}")
            
            # Watch config directory
            config_dir = Path('config')
            if config_dir.exists():
                observer = Observer()
                handler = ConfigChangeHandler(self)
                observer.schedule(handler, str(config_dir), recursive=True)
                observer.start()
                self.observers.append(observer)
                logger.info(f"Watching configuration directory: {config_dir}")
                
        except Exception as e:
            logger.warning(f"Failed to start file watching: {e}")
    
    def _handle_config_change(self, file_path: Path):
        """Handle configuration file changes"""
        try:
            with self.lock:
                logger.info(f"Reloading configuration due to change in: {file_path}")
                
                # Reload settings
                old_settings = self.settings
                
                # Clear environment cache and reload
                from config.settings import reload_settings
                self.settings = reload_settings()
                
                # Validate new configuration
                validation_errors = self._validate_configuration()
                
                if validation_errors:
                    logger.error(f"Configuration validation failed after reload: {validation_errors}")
                    # Revert to old settings
                    self.settings = old_settings
                    return
                
                self.last_reload = datetime.now()
                self.reload_count += 1
                
                # Notify callbacks
                for callback in self.change_callbacks:
                    try:
                        callback(self.settings)
                    except Exception as e:
                        logger.error(f"Error in configuration change callback: {e}")
                
                logger.info("Configuration reloaded successfully")
                
        except Exception as e:
            logger.error(f"Error handling configuration change: {e}")
    
    def _validate_configuration(self) -> List[str]:
        """Validate current configuration"""
        errors = []
        
        try:
            # Convert settings to dict for validation
            config_dict = self.settings.dict()
            
            # Validate required fields
            missing_fields = ConfigValidator.validate_required_fields(config_dict, self.required_fields)
            if missing_fields:
                errors.extend([f"Missing required field: {field}" for field in missing_fields])
            
            # Validate field types
            type_errors = ConfigValidator.validate_field_types(config_dict, self.field_types)
            errors.extend(type_errors)
            
            # Validate field ranges
            range_errors = ConfigValidator.validate_field_ranges(config_dict, self.field_ranges)
            errors.extend(range_errors)
            
            # Environment-specific validation
            if self.settings.environment == Environment.PRODUCTION:
                if self.settings.debug:
                    errors.append("Debug mode must be disabled in production")
                    
                if len(self.settings.security.secret_key) < 64:
                    errors.append("Production secret key must be at least 64 characters")
            
            if errors:
                logger.error(f"Configuration validation errors: {errors}")
            else:
                logger.debug("Configuration validation passed")
                
        except Exception as e:
            errors.append(f"Configuration validation error: {e}")
            logger.error(f"Error during configuration validation: {e}")
        
        return errors
    
    def get_settings(self) -> Settings:
        """Get current settings"""
        with self.lock:
            return self.settings
    
    def reload_configuration(self) -> bool:
        """Manually reload configuration"""
        try:
            with self.lock:
                logger.info("Manually reloading configuration")
                
                # Reload settings
                from config.settings import reload_settings
                new_settings = reload_settings()
                
                # Validate new configuration
                old_settings = self.settings
                self.settings = new_settings
                
                validation_errors = self._validate_configuration()
                
                if validation_errors:
                    logger.error(f"Configuration validation failed: {validation_errors}")
                    # Revert to old settings
                    self.settings = old_settings
                    return False
                
                self.last_reload = datetime.now()
                self.reload_count += 1
                
                # Notify callbacks
                for callback in self.change_callbacks:
                    try:
                        callback(self.settings)
                    except Exception as e:
                        logger.error(f"Error in configuration change callback: {e}")
                
                logger.info("Configuration reloaded successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error reloading configuration: {e}")
            return False
    
    def add_change_callback(self, callback: Callable[[Settings], None]):
        """Add a callback to be called when configuration changes"""
        with self.lock:
            self.change_callbacks.append(callback)
            logger.debug(f"Added configuration change callback: {callback.__name__}")
    
    def remove_change_callback(self, callback: Callable[[Settings], None]):
        """Remove a configuration change callback"""
        with self.lock:
            if callback in self.change_callbacks:
                self.change_callbacks.remove(callback)
                logger.debug(f"Removed configuration change callback: {callback.__name__}")
    
    def get_configuration_info(self) -> Dict[str, Any]:
        """Get configuration manager information"""
        with self.lock:
            return {
                "environment": self.settings.environment.value,
                "debug": self.settings.debug,
                "last_reload": self.last_reload.isoformat(),
                "reload_count": self.reload_count,
                "watching_files": self.watch_files,
                "active_observers": len(self.observers),
                "change_callbacks": len(self.change_callbacks),
                "validation_status": "passed" if not self._validate_configuration() else "failed"
            }
    
    def export_configuration(self, file_path: str, include_secrets: bool = False) -> bool:
        """Export current configuration to file"""
        try:
            with self.lock:
                config_dict = self.settings.dict()
                
                # Remove secrets if not included
                if not include_secrets:
                    sensitive_fields = [
                        'codegen.api_token',
                        'github.token',
                        'cloudflare.api_key',
                        'gemini.api_key',
                        'security.secret_key',
                        'security.webhook_secret'
                    ]
                    
                    for field in sensitive_fields:
                        parts = field.split('.')
                        current = config_dict
                        
                        try:
                            for part in parts[:-1]:
                                current = current[part]
                            if parts[-1] in current:
                                current[parts[-1]] = "[REDACTED]"
                        except (KeyError, TypeError):
                            pass
                
                # Write to file
                output_path = Path(file_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w') as f:
                    json.dump(config_dict, f, indent=2, default=str)
                
                logger.info(f"Configuration exported to: {file_path}")
                return True
                
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            return False
    
    def validate_configuration_file(self, file_path: str) -> List[str]:
        """Validate a configuration file without loading it"""
        try:
            # Load configuration from file
            with open(file_path, 'r') as f:
                if file_path.endswith('.json'):
                    config_dict = json.load(f)
                else:
                    # For .env files, we'd need to parse them
                    # For now, just return empty list
                    return []
            
            # Validate the loaded configuration
            errors = []
            
            missing_fields = ConfigValidator.validate_required_fields(config_dict, self.required_fields)
            if missing_fields:
                errors.extend([f"Missing required field: {field}" for field in missing_fields])
            
            type_errors = ConfigValidator.validate_field_types(config_dict, self.field_types)
            errors.extend(type_errors)
            
            range_errors = ConfigValidator.validate_field_ranges(config_dict, self.field_ranges)
            errors.extend(range_errors)
            
            return errors
            
        except Exception as e:
            return [f"Error validating configuration file: {e}"]
    
    def close(self):
        """Close the configuration manager and stop file watching"""
        logger.info("Closing configuration manager")
        
        # Stop file observers
        for observer in self.observers:
            try:
                observer.stop()
                observer.join(timeout=5)
            except Exception as e:
                logger.warning(f"Error stopping file observer: {e}")
        
        self.observers.clear()
        self.change_callbacks.clear()
        
        logger.info("Configuration manager closed")


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(watch_files: bool = True) -> ConfigManager:
    """Get or create the global configuration manager instance"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(watch_files=watch_files)
        
    return _config_manager


def close_config_manager():
    """Close the global configuration manager"""
    global _config_manager
    
    if _config_manager:
        _config_manager.close()
        _config_manager = None


# Convenience functions
def get_current_settings() -> Settings:
    """Get current settings from the configuration manager"""
    return get_config_manager().get_settings()


def reload_configuration() -> bool:
    """Reload configuration"""
    return get_config_manager().reload_configuration()


def add_config_change_callback(callback: Callable[[Settings], None]):
    """Add a configuration change callback"""
    get_config_manager().add_change_callback(callback)

