"""
Prometheus Metrics Collector
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Provides application metrics for monitoring and alerting.
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, REGISTRY
from typing import Dict, Optional
import time
import psutil


# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

# Generation metrics
sprite_generation_requests = Counter(
    'sprite_generation_requests_total',
    'Total sprite generation requests',
    ['status']  # success, failed, timeout
)

sprite_generation_duration_seconds = Histogram(
    'sprite_generation_duration_seconds',
    'Sprite generation duration in seconds',
    buckets=(30, 60, 120, 180, 240, 300, 360, 420, 480, 540, 600)  # 30s to 10min
)

sprite_validation_failures = Counter(
    'sprite_validation_failures_total',
    'Total sprite validation failures',
    ['reason']  # wrong_dimensions, inconsistent_palette, blank_frame, missing_frame
)

# PM Agent metrics
pm_agent_requests = Counter(
    'pm_agent_requests_total',
    'Total PM agent requests',
    ['requires_approval']  # true, false
)

pm_agent_response_duration_seconds = Histogram(
    'pm_agent_response_duration_seconds',
    'PM agent response time in seconds',
    buckets=(0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0)
)

# Knowledge base metrics
knowledge_base_searches = Counter(
    'knowledge_base_searches_total',
    'Total knowledge base searches'
)

knowledge_base_documents = Gauge(
    'knowledge_base_documents',
    'Number of documents in knowledge base',
    ['type']  # project_doc, conversation, task
)

# Service health metrics
service_health = Gauge(
    'service_health',
    'Service health status (1=healthy, 0=unhealthy)',
    ['service']  # ollama, comfyui
)

service_latency_seconds = Gauge(
    'service_latency_seconds',
    'Service response latency',
    ['service']
)

# System resource metrics
system_cpu_percent = Gauge(
    'system_cpu_percent',
    'CPU usage percentage'
)

system_memory_percent = Gauge(
    'system_memory_percent',
    'Memory usage percentage'
)

system_disk_percent = Gauge(
    'system_disk_percent',
    'Disk usage percentage'
)

# Application info
app_info = Info(
    'app',
    'Application information'
)


class MetricsCollector:
    """
    Centralized metrics collection and reporting.
    
    Usage:
        metrics = MetricsCollector()
        
        # Track HTTP request
        with metrics.track_request('POST', '/api/v1/prompt'):
            # ... handle request
            pass
        
        # Track generation
        with metrics.track_generation():
            # ... generate sprite
            pass
        
        # Update service health
        metrics.update_service_health('ollama', healthy=True, latency_ms=45)
    """
    
    def __init__(self):
        self.app_start_time = time.time()
        
        # Set application info
        app_info.info({
            'version': '3.2',
            'platform': 'intel-mac',
            'python_version': '3.11'
        })
    
    def track_request(self, method: str, endpoint: str):
        """
        Context manager for tracking HTTP requests.
        
        Usage:
            with metrics.track_request('POST', '/api/v1/prompt'):
                # Handle request
                pass
        """
        return RequestTracker(method, endpoint)
    
    def track_generation(self):
        """
        Context manager for tracking sprite generation.
        
        Usage:
            with metrics.track_generation():
                # Generate sprite
                pass
        """
        return GenerationTracker()
    
    def record_validation_failure(self, reason: str):
        """Record sprite validation failure."""
        sprite_validation_failures.labels(reason=reason).inc()
    
    def record_pm_agent_request(self, requires_approval: bool, duration_seconds: float):
        """Record PM agent request metrics."""
        pm_agent_requests.labels(
            requires_approval=str(requires_approval).lower()
        ).inc()
        pm_agent_response_duration_seconds.observe(duration_seconds)

    def record_art_generation(self, success: bool, duration_seconds: float):
        """Record art generation metrics."""
        status = 'success' if success else 'failed'
        sprite_generation_requests.labels(status=status).inc()
        if duration_seconds > 0:
            sprite_generation_duration_seconds.observe(duration_seconds)

    def record_knowledge_base_search(self):
        """Record knowledge base search."""
        knowledge_base_searches.inc()
    
    def update_knowledge_base_size(self, doc_type: str, count: int):
        """Update knowledge base document count."""
        knowledge_base_documents.labels(type=doc_type).set(count)
    
    def update_service_health(
        self,
        service: str,
        healthy: bool,
        latency_ms: Optional[float] = None
    ):
        """
        Update service health status.
        
        Args:
            service: Service name (ollama, comfyui)
            healthy: True if service is healthy
            latency_ms: Response latency in milliseconds
        """
        service_health.labels(service=service).set(1 if healthy else 0)
        
        if latency_ms is not None:
            service_latency_seconds.labels(service=service).set(latency_ms / 1000)
    
    def update_system_metrics(self):
        """Update system resource metrics."""
        system_cpu_percent.set(psutil.cpu_percent(interval=1))
        system_memory_percent.set(psutil.virtual_memory().percent)
        system_disk_percent.set(psutil.disk_usage('/').percent)
    
    def get_uptime_seconds(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self.app_start_time
    
    def export_metrics(self) -> bytes:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Prometheus-formatted metrics as bytes
        """
        return generate_latest(REGISTRY)


class RequestTracker:
    """Context manager for tracking HTTP request metrics."""
    
    def __init__(self, method: str, endpoint: str):
        self.method = method
        self.endpoint = endpoint
        self.start_time = None
        self.status = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        # Determine status
        if exc_type is None:
            self.status = self.status or '200'
        else:
            self.status = '500'
        
        # Record metrics
        http_requests_total.labels(
            method=self.method,
            endpoint=self.endpoint,
            status=self.status
        ).inc()
        
        http_request_duration_seconds.labels(
            method=self.method,
            endpoint=self.endpoint
        ).observe(duration)
        
        return False  # Don't suppress exceptions
    
    def set_status(self, status: str):
        """Set HTTP status code."""
        self.status = status


class GenerationTracker:
    """Context manager for tracking sprite generation metrics."""
    
    def __init__(self):
        self.start_time = None
        self.status = 'success'
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        # Determine status
        if exc_type is not None:
            if 'timeout' in str(exc_val).lower():
                self.status = 'timeout'
            else:
                self.status = 'failed'
        
        # Record metrics
        sprite_generation_requests.labels(status=self.status).inc()
        sprite_generation_duration_seconds.observe(duration)
        
        return False
    
    def set_status(self, status: str):
        """Set generation status (success, failed, timeout)."""
        self.status = status


# Global metrics instance
metrics = MetricsCollector()
