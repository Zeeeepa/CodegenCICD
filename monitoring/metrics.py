"""
Metrics Collection and Monitoring

This module provides comprehensive metrics collection, monitoring,
and alerting capabilities for the application.
"""

import asyncio
import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum

from config.settings import MonitoringSettings, get_settings


class MetricType(str, Enum):
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricValue:
    """Represents a metric value with timestamp"""
    value: Union[int, float]
    timestamp: datetime
    labels: Dict[str, str]


@dataclass
class Alert:
    """Represents an alert"""
    name: str
    severity: AlertSeverity
    message: str
    metric_name: str
    current_value: Union[int, float]
    threshold: Union[int, float]
    timestamp: datetime
    resolved: bool = False


class Metric:
    """Base metric class"""
    
    def __init__(self, name: str, description: str, labels: Optional[Dict[str, str]] = None):
        self.name = name
        self.description = description
        self.labels = labels or {}
        self.values: deque = deque(maxlen=1000)  # Keep last 1000 values
        self.lock = threading.Lock()
    
    def add_value(self, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """Add a value to the metric"""
        with self.lock:
            metric_labels = {**self.labels, **(labels or {})}
            self.values.append(MetricValue(value, datetime.now(), metric_labels))
    
    def get_current_value(self) -> Optional[Union[int, float]]:
        """Get the current (most recent) value"""
        with self.lock:
            if self.values:
                return self.values[-1].value
            return None
    
    def get_values(self, since: Optional[datetime] = None) -> List[MetricValue]:
        """Get values since a specific time"""
        with self.lock:
            if since is None:
                return list(self.values)
            return [v for v in self.values if v.timestamp >= since]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get metric statistics"""
        with self.lock:
            if not self.values:
                return {
                    "name": self.name,
                    "description": self.description,
                    "count": 0,
                    "current_value": None,
                    "min": None,
                    "max": None,
                    "avg": None
                }
            
            values = [v.value for v in self.values]
            return {
                "name": self.name,
                "description": self.description,
                "count": len(values),
                "current_value": values[-1],
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values)
            }


class Counter(Metric):
    """Counter metric - monotonically increasing"""
    
    def __init__(self, name: str, description: str, labels: Optional[Dict[str, str]] = None):
        super().__init__(name, description, labels)
        self.count = 0
    
    def increment(self, amount: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None):
        """Increment the counter"""
        with self.lock:
            self.count += amount
            self.add_value(self.count, labels)
    
    def get_count(self) -> Union[int, float]:
        """Get current count"""
        with self.lock:
            return self.count


class Gauge(Metric):
    """Gauge metric - can go up and down"""
    
    def set(self, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """Set the gauge value"""
        self.add_value(value, labels)
    
    def increment(self, amount: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None):
        """Increment the gauge"""
        current = self.get_current_value() or 0
        self.set(current + amount, labels)
    
    def decrement(self, amount: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None):
        """Decrement the gauge"""
        current = self.get_current_value() or 0
        self.set(current - amount, labels)


class Histogram(Metric):
    """Histogram metric - tracks distribution of values"""
    
    def __init__(self, name: str, description: str, buckets: Optional[List[float]] = None, 
                 labels: Optional[Dict[str, str]] = None):
        super().__init__(name, description, labels)
        self.buckets = buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf')]
        self.bucket_counts = defaultdict(int)
        self.sum = 0
        self.count = 0
    
    def observe(self, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """Observe a value"""
        with self.lock:
            self.add_value(value, labels)
            self.sum += value
            self.count += 1
            
            # Update bucket counts
            for bucket in self.buckets:
                if value <= bucket:
                    self.bucket_counts[bucket] += 1
    
    def get_histogram_stats(self) -> Dict[str, Any]:
        """Get histogram statistics"""
        with self.lock:
            return {
                "name": self.name,
                "description": self.description,
                "count": self.count,
                "sum": self.sum,
                "avg": self.sum / self.count if self.count > 0 else 0,
                "buckets": dict(self.bucket_counts)
            }


class Timer(Metric):
    """Timer metric - measures duration"""
    
    def __init__(self, name: str, description: str, labels: Optional[Dict[str, str]] = None):
        super().__init__(name, description, labels)
        self.histogram = Histogram(f"{name}_duration", f"{description} duration")
    
    def time(self, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing operations"""
        return TimerContext(self, labels)
    
    def record(self, duration: float, labels: Optional[Dict[str, str]] = None):
        """Record a duration"""
        self.add_value(duration, labels)
        self.histogram.observe(duration, labels)
    
    def get_timer_stats(self) -> Dict[str, Any]:
        """Get timer statistics"""
        return self.histogram.get_histogram_stats()


class TimerContext:
    """Context manager for timing operations"""
    
    def __init__(self, timer: Timer, labels: Optional[Dict[str, str]] = None):
        self.timer = timer
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.timer.record(duration, self.labels)


class AlertRule:
    """Alert rule for monitoring metrics"""
    
    def __init__(
        self,
        name: str,
        metric_name: str,
        condition: str,  # e.g., "gt", "lt", "eq"
        threshold: Union[int, float],
        severity: AlertSeverity = AlertSeverity.WARNING,
        duration: int = 60,  # seconds
        message_template: str = "Alert: {metric_name} is {current_value} (threshold: {threshold})"
    ):
        self.name = name
        self.metric_name = metric_name
        self.condition = condition
        self.threshold = threshold
        self.severity = severity
        self.duration = duration
        self.message_template = message_template
        self.triggered_at: Optional[datetime] = None
        self.last_alert: Optional[datetime] = None
    
    def check(self, current_value: Union[int, float]) -> Optional[Alert]:
        """Check if alert should be triggered"""
        should_trigger = False
        
        if self.condition == "gt" and current_value > self.threshold:
            should_trigger = True
        elif self.condition == "lt" and current_value < self.threshold:
            should_trigger = True
        elif self.condition == "eq" and current_value == self.threshold:
            should_trigger = True
        elif self.condition == "gte" and current_value >= self.threshold:
            should_trigger = True
        elif self.condition == "lte" and current_value <= self.threshold:
            should_trigger = True
        
        now = datetime.now()
        
        if should_trigger:
            if self.triggered_at is None:
                self.triggered_at = now
            
            # Check if duration has passed
            if (now - self.triggered_at).total_seconds() >= self.duration:
                # Check if we should send alert (avoid spam)
                if (self.last_alert is None or 
                    (now - self.last_alert).total_seconds() >= 300):  # 5 minutes
                    
                    self.last_alert = now
                    message = self.message_template.format(
                        metric_name=self.metric_name,
                        current_value=current_value,
                        threshold=self.threshold
                    )
                    
                    return Alert(
                        name=self.name,
                        severity=self.severity,
                        message=message,
                        metric_name=self.metric_name,
                        current_value=current_value,
                        threshold=self.threshold,
                        timestamp=now
                    )
        else:
            self.triggered_at = None
        
        return None


class MetricsCollector:
    """Main metrics collector"""
    
    def __init__(self, settings: Optional[MonitoringSettings] = None):
        self.settings = settings or get_settings().monitoring
        self.metrics: Dict[str, Metric] = {}
        self.alert_rules: Dict[str, AlertRule] = {}
        self.alerts: List[Alert] = []
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        self.lock = threading.Lock()
        self.logger = logging.getLogger('metrics')
        
        # Background task for checking alerts
        self.alert_check_task = None
        if self.settings.enable_alerting:
            self._start_alert_checking()
    
    def register_metric(self, metric: Metric):
        """Register a metric"""
        with self.lock:
            self.metrics[metric.name] = metric
            self.logger.info(f"Registered metric: {metric.name}")
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name"""
        with self.lock:
            return self.metrics.get(name)
    
    def create_counter(self, name: str, description: str, 
                      labels: Optional[Dict[str, str]] = None) -> Counter:
        """Create and register a counter metric"""
        counter = Counter(name, description, labels)
        self.register_metric(counter)
        return counter
    
    def create_gauge(self, name: str, description: str, 
                    labels: Optional[Dict[str, str]] = None) -> Gauge:
        """Create and register a gauge metric"""
        gauge = Gauge(name, description, labels)
        self.register_metric(gauge)
        return gauge
    
    def create_histogram(self, name: str, description: str, 
                        buckets: Optional[List[float]] = None,
                        labels: Optional[Dict[str, str]] = None) -> Histogram:
        """Create and register a histogram metric"""
        histogram = Histogram(name, description, buckets, labels)
        self.register_metric(histogram)
        return histogram
    
    def create_timer(self, name: str, description: str, 
                    labels: Optional[Dict[str, str]] = None) -> Timer:
        """Create and register a timer metric"""
        timer = Timer(name, description, labels)
        self.register_metric(timer)
        return timer
    
    def add_alert_rule(self, rule: AlertRule):
        """Add an alert rule"""
        with self.lock:
            self.alert_rules[rule.name] = rule
            self.logger.info(f"Added alert rule: {rule.name}")
    
    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """Add an alert callback"""
        self.alert_callbacks.append(callback)
    
    def _start_alert_checking(self):
        """Start background alert checking"""
        def check_alerts():
            while True:
                try:
                    self._check_all_alerts()
                    time.sleep(self.settings.health_check_interval)
                except Exception as e:
                    self.logger.error(f"Error checking alerts: {e}")
                    time.sleep(10)
        
        alert_thread = threading.Thread(target=check_alerts, daemon=True)
        alert_thread.start()
        self.logger.info("Started alert checking thread")
    
    def _check_all_alerts(self):
        """Check all alert rules"""
        with self.lock:
            for rule in self.alert_rules.values():
                metric = self.metrics.get(rule.metric_name)
                if metric:
                    current_value = metric.get_current_value()
                    if current_value is not None:
                        alert = rule.check(current_value)
                        if alert:
                            self.alerts.append(alert)
                            self._notify_alert_callbacks(alert)
    
    def _notify_alert_callbacks(self, alert: Alert):
        """Notify alert callbacks"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
    
    def get_all_metrics_stats(self) -> Dict[str, Any]:
        """Get statistics for all metrics"""
        with self.lock:
            stats = {}
            for name, metric in self.metrics.items():
                if isinstance(metric, Histogram):
                    stats[name] = metric.get_histogram_stats()
                elif isinstance(metric, Timer):
                    stats[name] = metric.get_timer_stats()
                else:
                    stats[name] = metric.get_stats()
            return stats
    
    def get_alerts(self, since: Optional[datetime] = None) -> List[Alert]:
        """Get alerts since a specific time"""
        with self.lock:
            if since is None:
                return list(self.alerts)
            return [alert for alert in self.alerts if alert.timestamp >= since]
    
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format"""
        stats = self.get_all_metrics_stats()
        
        if format == "json":
            return json.dumps(stats, indent=2, default=str)
        elif format == "prometheus":
            return self._export_prometheus_format(stats)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_prometheus_format(self, stats: Dict[str, Any]) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        for name, metric_stats in stats.items():
            # Add help and type comments
            lines.append(f"# HELP {name} {metric_stats.get('description', '')}")
            
            if 'buckets' in metric_stats:
                lines.append(f"# TYPE {name} histogram")
                # Export histogram buckets
                for bucket, count in metric_stats['buckets'].items():
                    lines.append(f'{name}_bucket{{le="{bucket}"}} {count}')
                lines.append(f'{name}_sum {metric_stats["sum"]}')
                lines.append(f'{name}_count {metric_stats["count"]}')
            else:
                lines.append(f"# TYPE {name} gauge")
                current_value = metric_stats.get('current_value', 0)
                lines.append(f'{name} {current_value}')
        
        return '\n'.join(lines)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        with self.lock:
            recent_alerts = self.get_alerts(datetime.now() - timedelta(minutes=5))
            critical_alerts = [a for a in recent_alerts if a.severity == AlertSeverity.CRITICAL]
            
            return {
                "healthy": len(critical_alerts) == 0,
                "metrics_count": len(self.metrics),
                "alert_rules_count": len(self.alert_rules),
                "recent_alerts_count": len(recent_alerts),
                "critical_alerts_count": len(critical_alerts),
                "timestamp": datetime.now().isoformat()
            }


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector(settings: Optional[MonitoringSettings] = None) -> MetricsCollector:
    """Get or create the global metrics collector instance"""
    global _metrics_collector
    
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(settings)
    
    return _metrics_collector


# Convenience functions
def create_counter(name: str, description: str, 
                  labels: Optional[Dict[str, str]] = None) -> Counter:
    """Create a counter metric"""
    return get_metrics_collector().create_counter(name, description, labels)


def create_gauge(name: str, description: str, 
                labels: Optional[Dict[str, str]] = None) -> Gauge:
    """Create a gauge metric"""
    return get_metrics_collector().create_gauge(name, description, labels)


def create_histogram(name: str, description: str, 
                    buckets: Optional[List[float]] = None,
                    labels: Optional[Dict[str, str]] = None) -> Histogram:
    """Create a histogram metric"""
    return get_metrics_collector().create_histogram(name, description, buckets, labels)


def create_timer(name: str, description: str, 
                labels: Optional[Dict[str, str]] = None) -> Timer:
    """Create a timer metric"""
    return get_metrics_collector().create_timer(name, description, labels)


def add_alert_rule(rule: AlertRule):
    """Add an alert rule"""
    get_metrics_collector().add_alert_rule(rule)


def get_metric(name: str) -> Optional[Metric]:
    """Get a metric by name"""
    return get_metrics_collector().get_metric(name)


# Decorator for timing functions
def timed(metric_name: str, description: str = "", 
          labels: Optional[Dict[str, str]] = None):
    """Decorator to time function execution"""
    def decorator(func):
        timer = create_timer(metric_name, description or f"Timer for {func.__name__}", labels)
        
        def wrapper(*args, **kwargs):
            with timer.time():
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Context manager for custom metrics
class metric_context:
    """Context manager for recording metrics"""
    
    def __init__(self, metric: Metric, labels: Optional[Dict[str, str]] = None):
        self.metric = metric
        self.labels = labels
        self.start_time = None
        self.start_value = None
    
    def __enter__(self):
        if isinstance(self.metric, Timer):
            self.start_time = time.time()
        elif isinstance(self.metric, (Counter, Gauge)):
            self.start_value = self.metric.get_current_value() or 0
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(self.metric, Timer) and self.start_time:
            duration = time.time() - self.start_time
            self.metric.record(duration, self.labels)
        elif isinstance(self.metric, Counter):
            # Increment counter on exit
            self.metric.increment(1, self.labels)
        elif isinstance(self.metric, Gauge) and self.start_value is not None:
            # Record final value
            current_value = self.metric.get_current_value() or 0
            self.metric.set(current_value, self.labels)

