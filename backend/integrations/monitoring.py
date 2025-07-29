"""
Comprehensive logging and monitoring system for Codegen API client
"""
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from collections import defaultdict, deque
from threading import Lock
import structlog
from dataclasses import dataclass, field
import asyncio


@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    timestamp: datetime
    method: str
    endpoint: str
    status_code: Optional[int]
    response_time_ms: float
    request_size_bytes: int
    response_size_bytes: int
    success: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class PerformanceStats:
    """Performance statistics over a time period"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time_ms: float = 0.0
    min_response_time_ms: float = float('inf')
    max_response_time_ms: float = 0.0
    p50_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    error_rate: float = 0.0
    requests_per_second: float = 0.0


class MetricsCollector:
    """Collects and aggregates API metrics"""
    
    def __init__(self, max_metrics: int = 10000, retention_hours: int = 24):
        self.max_metrics = max_metrics
        self.retention_hours = retention_hours
        self._metrics: deque = deque(maxlen=max_metrics)
        self._lock = Lock()
        
        # Aggregated stats by endpoint
        self._endpoint_stats: Dict[str, List[RequestMetrics]] = defaultdict(list)
        
        # Error tracking
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._error_details: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Rate limiting stats
        self._rate_limit_events: List[Dict[str, Any]] = []
        
        # Performance tracking
        self._response_times: deque = deque(maxlen=1000)  # Keep last 1000 response times
    
    def record_request(self, metrics: RequestMetrics):
        """Record metrics for a single request"""
        with self._lock:
            # Add to main metrics collection
            self._metrics.append(metrics)
            
            # Add to endpoint-specific stats
            self._endpoint_stats[metrics.endpoint].append(metrics)
            
            # Track errors
            if not metrics.success and metrics.error_type:
                self._error_counts[metrics.error_type] += 1
                self._error_details[metrics.error_type].append({
                    'timestamp': metrics.timestamp.isoformat(),
                    'endpoint': metrics.endpoint,
                    'status_code': metrics.status_code,
                    'message': metrics.error_message,
                    'request_id': metrics.request_id
                })
            
            # Track response times
            self._response_times.append(metrics.response_time_ms)
            
            # Clean up old data
            self._cleanup_old_data()
    
    def record_rate_limit_event(self, endpoint: str, retry_after: int, timestamp: Optional[datetime] = None):
        """Record a rate limiting event"""
        with self._lock:
            event = {
                'timestamp': (timestamp or datetime.utcnow()).isoformat(),
                'endpoint': endpoint,
                'retry_after': retry_after
            }
            self._rate_limit_events.append(event)
            
            # Keep only recent events
            cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
            self._rate_limit_events = [
                event for event in self._rate_limit_events
                if datetime.fromisoformat(event['timestamp']) > cutoff_time
            ]
    
    def _cleanup_old_data(self):
        """Remove old metrics data"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
        
        # Clean up endpoint stats
        for endpoint in list(self._endpoint_stats.keys()):
            self._endpoint_stats[endpoint] = [
                metric for metric in self._endpoint_stats[endpoint]
                if metric.timestamp > cutoff_time
            ]
            if not self._endpoint_stats[endpoint]:
                del self._endpoint_stats[endpoint]
        
        # Clean up error details
        for error_type in list(self._error_details.keys()):
            self._error_details[error_type] = [
                error for error in self._error_details[error_type]
                if datetime.fromisoformat(error['timestamp']) > cutoff_time
            ]
            if not self._error_details[error_type]:
                del self._error_details[error_type]
    
    def get_performance_stats(self, 
                            endpoint: Optional[str] = None,
                            time_window_hours: int = 1) -> PerformanceStats:
        """Get performance statistics for a time window"""
        with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            
            # Filter metrics
            if endpoint:
                relevant_metrics = [
                    m for m in self._endpoint_stats.get(endpoint, [])
                    if m.timestamp > cutoff_time
                ]
            else:
                relevant_metrics = [
                    m for m in self._metrics
                    if m.timestamp > cutoff_time
                ]
            
            if not relevant_metrics:
                return PerformanceStats()
            
            # Calculate statistics
            total_requests = len(relevant_metrics)
            successful_requests = sum(1 for m in relevant_metrics if m.success)
            failed_requests = total_requests - successful_requests
            
            response_times = [m.response_time_ms for m in relevant_metrics]
            response_times.sort()
            
            stats = PerformanceStats(
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                average_response_time_ms=sum(response_times) / len(response_times),
                min_response_time_ms=min(response_times),
                max_response_time_ms=max(response_times),
                p50_response_time_ms=self._percentile(response_times, 50),
                p95_response_time_ms=self._percentile(response_times, 95),
                p99_response_time_ms=self._percentile(response_times, 99),
                total_bytes_sent=sum(m.request_size_bytes for m in relevant_metrics),
                total_bytes_received=sum(m.response_size_bytes for m in relevant_metrics),
                error_rate=(failed_requests / total_requests) * 100 if total_requests > 0 else 0,
                requests_per_second=total_requests / (time_window_hours * 3600)
            )
            
            return stats
    
    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values"""
        if not sorted_values:
            return 0.0
        
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def get_error_summary(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get error summary for a time window"""
        with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            
            # Filter recent errors
            recent_errors = {}
            for error_type, errors in self._error_details.items():
                recent_errors[error_type] = [
                    error for error in errors
                    if datetime.fromisoformat(error['timestamp']) > cutoff_time
                ]
            
            # Calculate error rates by endpoint
            endpoint_errors = defaultdict(int)
            for errors in recent_errors.values():
                for error in errors:
                    endpoint_errors[error['endpoint']] += 1
            
            return {
                'error_counts': {k: len(v) for k, v in recent_errors.items()},
                'error_details': recent_errors,
                'endpoint_error_counts': dict(endpoint_errors),
                'total_errors': sum(len(v) for v in recent_errors.values()),
                'rate_limit_events': len([
                    event for event in self._rate_limit_events
                    if datetime.fromisoformat(event['timestamp']) > cutoff_time
                ])
            }
    
    def get_endpoint_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics broken down by endpoint"""
        with self._lock:
            endpoint_stats = {}
            
            for endpoint in self._endpoint_stats:
                stats = self.get_performance_stats(endpoint=endpoint)
                endpoint_stats[endpoint] = {
                    'total_requests': stats.total_requests,
                    'success_rate': (stats.successful_requests / stats.total_requests * 100) if stats.total_requests > 0 else 0,
                    'average_response_time_ms': stats.average_response_time_ms,
                    'error_rate': stats.error_rate
                }
            
            return endpoint_stats
    
    def export_metrics(self, format: str = 'json') -> str:
        """Export metrics in specified format"""
        with self._lock:
            data = {
                'export_timestamp': datetime.utcnow().isoformat(),
                'performance_stats': self.get_performance_stats().__dict__,
                'error_summary': self.get_error_summary(),
                'endpoint_stats': self.get_endpoint_stats(),
                'rate_limit_events': self._rate_limit_events[-100:]  # Last 100 events
            }
            
            if format.lower() == 'json':
                return json.dumps(data, indent=2, default=str)
            else:
                raise ValueError(f"Unsupported export format: {format}")


class EnhancedLogger:
    """Enhanced logger with structured logging and metrics collection"""
    
    def __init__(self, 
                 service_name: str = "codegen_client",
                 log_level: str = "INFO",
                 enable_metrics: bool = True,
                 log_requests: bool = True,
                 log_responses: bool = False,
                 log_sensitive_data: bool = False):
        self.service_name = service_name
        self.log_level = log_level
        self.enable_metrics = enable_metrics
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_sensitive_data = log_sensitive_data
        
        # Set up structured logger
        self.logger = structlog.get_logger(service_name)
        
        # Set up metrics collector
        self.metrics_collector = MetricsCollector() if enable_metrics else None
        
        # Request context storage
        self._request_contexts: Dict[str, Dict[str, Any]] = {}
        self._context_lock = Lock()
    
    def start_request(self, 
                     request_id: str,
                     method: str,
                     endpoint: str,
                     request_size: int = 0,
                     **context) -> Dict[str, Any]:
        """Start tracking a request"""
        request_context = {
            'request_id': request_id,
            'method': method,
            'endpoint': endpoint,
            'start_time': time.time(),
            'request_size': request_size,
            **context
        }
        
        with self._context_lock:
            self._request_contexts[request_id] = request_context
        
        if self.log_requests:
            self.logger.info(
                "API request started",
                request_id=request_id,
                method=method,
                endpoint=endpoint,
                **self._filter_sensitive_data(context)
            )
        
        return request_context
    
    def end_request(self,
                   request_id: str,
                   status_code: Optional[int] = None,
                   response_size: int = 0,
                   error: Optional[Exception] = None,
                   **context):
        """End tracking a request and record metrics"""
        with self._context_lock:
            request_context = self._request_contexts.pop(request_id, {})
        
        if not request_context:
            self.logger.warning("Request context not found", request_id=request_id)
            return
        
        # Calculate metrics
        end_time = time.time()
        response_time_ms = (end_time - request_context['start_time']) * 1000
        success = error is None and (status_code is None or 200 <= status_code < 400)
        
        # Log the completion
        log_data = {
            'request_id': request_id,
            'method': request_context['method'],
            'endpoint': request_context['endpoint'],
            'status_code': status_code,
            'response_time_ms': round(response_time_ms, 2),
            'success': success,
            **self._filter_sensitive_data(context)
        }
        
        if error:
            log_data['error'] = str(error)
            log_data['error_type'] = type(error).__name__
            self.logger.error("API request failed", **log_data)
        else:
            self.logger.info("API request completed", **log_data)
        
        # Record metrics
        if self.metrics_collector:
            metrics = RequestMetrics(
                timestamp=datetime.utcnow(),
                method=request_context['method'],
                endpoint=request_context['endpoint'],
                status_code=status_code,
                response_time_ms=response_time_ms,
                request_size_bytes=request_context.get('request_size', 0),
                response_size_bytes=response_size,
                success=success,
                error_type=type(error).__name__ if error else None,
                error_message=str(error) if error else None,
                request_id=request_id
            )
            self.metrics_collector.record_request(metrics)
    
    def log_rate_limit(self, endpoint: str, retry_after: int, request_id: Optional[str] = None):
        """Log a rate limiting event"""
        self.logger.warning(
            "Rate limit encountered",
            endpoint=endpoint,
            retry_after=retry_after,
            request_id=request_id
        )
        
        if self.metrics_collector:
            self.metrics_collector.record_rate_limit_event(endpoint, retry_after)
    
    def _filter_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from logs"""
        if self.log_sensitive_data:
            return data
        
        filtered = {}
        sensitive_keys = {'authorization', 'token', 'password', 'secret', 'key'}
        
        for key, value in data.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                filtered[key] = '[REDACTED]'
            else:
                filtered[key] = value
        
        return filtered
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        if not self.metrics_collector:
            return {'metrics_disabled': True}
        
        return {
            'performance_stats': self.metrics_collector.get_performance_stats().__dict__,
            'error_summary': self.metrics_collector.get_error_summary(),
            'endpoint_stats': self.metrics_collector.get_endpoint_stats()
        }
    
    def export_metrics(self, format: str = 'json') -> Optional[str]:
        """Export metrics data"""
        if not self.metrics_collector:
            return None
        
        return self.metrics_collector.export_metrics(format)


class HealthChecker:
    """Health checking and monitoring for the API client"""
    
    def __init__(self, logger: EnhancedLogger):
        self.logger = logger
        self._health_checks: Dict[str, Callable] = {}
        self._health_history: deque = deque(maxlen=100)
        self._lock = Lock()
    
    def register_health_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self._health_checks[name] = check_func
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all registered health checks"""
        results = {}
        overall_healthy = True
        
        for name, check_func in self._health_checks.items():
            try:
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                response_time = (time.time() - start_time) * 1000
                
                check_result = {
                    'status': 'healthy',
                    'response_time_ms': round(response_time, 2),
                    'details': result if isinstance(result, dict) else {'result': result}
                }
                
            except Exception as e:
                overall_healthy = False
                check_result = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'error_type': type(e).__name__
                }
                
                self.logger.logger.error(
                    "Health check failed",
                    check_name=name,
                    error=str(e)
                )
            
            results[name] = check_result
        
        # Record health check result
        health_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_healthy': overall_healthy,
            'checks': results
        }
        
        with self._lock:
            self._health_history.append(health_record)
        
        return {
            'overall_status': 'healthy' if overall_healthy else 'unhealthy',
            'timestamp': health_record['timestamp'],
            'checks': results
        }
    
    def get_health_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent health check history"""
        with self._lock:
            return list(self._health_history)[-limit:]


# Global instances
global_logger = EnhancedLogger()
global_health_checker = HealthChecker(global_logger)


def get_logger(service_name: str = "codegen_client") -> EnhancedLogger:
    """Get or create a logger instance"""
    return EnhancedLogger(service_name=service_name)


def setup_monitoring(config: Dict[str, Any]) -> EnhancedLogger:
    """Set up monitoring with configuration"""
    return EnhancedLogger(
        service_name=config.get('service_name', 'codegen_client'),
        log_level=config.get('log_level', 'INFO'),
        enable_metrics=config.get('enable_metrics', True),
        log_requests=config.get('log_requests', True),
        log_responses=config.get('log_responses', False),
        log_sensitive_data=config.get('log_sensitive_data', False)
    )

