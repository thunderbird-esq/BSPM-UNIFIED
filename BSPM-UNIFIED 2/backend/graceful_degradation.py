"""
Graceful Degradation Handler
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Allows system to continue operating with reduced functionality when services fail.
"""

import logging
import time
from typing import Optional, List, Dict, Any, Callable
from functools import wraps

logger = logging.getLogger(__name__)


class DegradedMode:
    """
    Tracks which services are in degraded mode.
    
    When a service fails, the system can continue operating with:
    - FAISS unavailable → Skip semantic search, use recent context only
    - Ollama unavailable → Return canned responses, queue for retry
    - ComfyUI unavailable → Queue generation requests for retry
    """
    
    def __init__(self):
        self.degraded_services: Dict[str, dict] = {}
    
    def mark_degraded(self, service: str, reason: str):
        """Mark a service as degraded."""
        self.degraded_services[service] = {
            'reason': reason,
            'marked_at': time.time()
        }
        logger.warning(
            f"Service {service} marked as degraded",
            extra={'service': service, 'reason': reason}
        )
    
    def mark_healthy(self, service: str):
        """Mark a service as healthy (remove from degraded list)."""
        if service in self.degraded_services:
            degraded_info = self.degraded_services.pop(service)
            duration = time.time() - degraded_info['marked_at']
            logger.info(
                f"Service {service} recovered",
                extra={
                    'service': service,
                    'degraded_duration_seconds': duration
                }
            )
    
    def is_degraded(self, service: str) -> bool:
        """Check if a service is currently degraded."""
        return service in self.degraded_services
    
    def get_status(self) -> Dict[str, Any]:
        """Get degradation status for all services."""
        return {
            service: {
                'reason': info['reason'],
                'duration_seconds': time.time() - info['marked_at']
            }
            for service, info in self.degraded_services.items()
        }


# Global degraded mode tracker
degraded_mode = DegradedMode()


def fallback_on_failure(
    fallback_func: Callable,
    service_name: str,
    exceptions: tuple = (Exception,)
):
    """
    Decorator that falls back to alternative function if primary fails.
    
    Args:
        fallback_func: Function to call if primary fails
        service_name: Service name for degradation tracking
        exceptions: Exceptions to catch
    
    Example:
        def search_with_recent_context_only(query, session_id):
            # Fallback implementation without FAISS
            return get_recent_conversation_turns(session_id, limit=3)
        
        @fallback_on_failure(
            fallback_func=search_with_recent_context_only,
            service_name='faiss'
        )
        def search_knowledge_base(query, session_id):
            # Primary implementation with FAISS
            return kb.hybrid_search(query, session_id)
    """
    def decorator(primary_func: Callable) -> Callable:
        @wraps(primary_func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                result = primary_func(*args, **kwargs)
                
                # If successful, mark service as healthy
                if degraded_mode.is_degraded(service_name):
                    degraded_mode.mark_healthy(service_name)
                
                return result
                
            except exceptions as e:
                logger.warning(
                    f"Primary function {primary_func.__name__} failed, "
                    f"falling back to {fallback_func.__name__}",
                    extra={
                        'primary_function': primary_func.__name__,
                        'fallback_function': fallback_func.__name__,
                        'service': service_name,
                        'exception': str(e)
                    }
                )
                
                # Mark service as degraded
                degraded_mode.mark_degraded(service_name, str(e))
                
                # Call fallback with same arguments
                return fallback_func(*args, **kwargs)
        
        return wrapper
    return decorator


def skip_on_failure(
    service_name: str,
    default_return: Any = None,
    exceptions: tuple = (Exception,)
):
    """
    Decorator that skips operation if it fails, returning default value.
    
    Useful for non-critical operations like metrics collection.
    
    Args:
        service_name: Service name for degradation tracking
        default_return: Value to return on failure
        exceptions: Exceptions to catch
    
    Example:
        @skip_on_failure(service_name='metrics', default_return=None)
        def record_metrics(operation, duration):
            # If this fails, just skip it
            prometheus_client.record(operation, duration)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
                
            except exceptions as e:
                logger.debug(
                    f"Non-critical operation {func.__name__} failed, skipping",
                    extra={
                        'function': func.__name__,
                        'service': service_name,
                        'exception': str(e)
                    }
                )
                
                degraded_mode.mark_degraded(service_name, str(e))
                return default_return
        
        return wrapper
    return decorator


class FallbackResponses:
    """
    Canned responses for when PM agent (Ollama) is unavailable.
    """
    
    @staticmethod
    def pm_agent_unavailable(user_message: str) -> dict:
        """
        Return canned response when Ollama is down.
        
        Returns dict matching PM agent response format.
        """
        return {
            'response_to_user': (
                "The AI assistant is temporarily unavailable. "
                "Your request has been queued and will be processed when the service recovers. "
                "You can continue using the system, but AI-powered features may be limited."
            ),
            'needs_approval': False,
            'delegation_plan': [],
            'degraded': True,
            'service': 'ollama'
        }
    
    @staticmethod
    def comfyui_unavailable() -> dict:
        """Return canned response when ComfyUI is down."""
        return {
            'status': 'queued',
            'message': (
                "The image generation service is temporarily unavailable. "
                "Your generation request has been queued and will be processed automatically "
                "when the service recovers."
            ),
            'degraded': True,
            'service': 'comfyui'
        }
    
    @staticmethod
    def knowledge_base_unavailable(query: str) -> List[dict]:
        """Return empty results when FAISS is down."""
        logger.info(
            "Knowledge base unavailable, returning empty search results",
            extra={'query': query}
        )
        return []


def get_degradation_warning() -> Optional[str]:
    """
    Get user-facing warning message if any services are degraded.
    
    Returns:
        Warning message or None if all services healthy
    """
    status = degraded_mode.get_status()
    
    if not status:
        return None
    
    degraded_services = list(status.keys())
    
    if len(degraded_services) == 1:
        service = degraded_services[0]
        return (
            f"⚠️ The {service} service is currently experiencing issues. "
            f"Some features may be unavailable or limited."
        )
    else:
        services_str = ", ".join(degraded_services)
        return (
            f"⚠️ Multiple services are experiencing issues: {services_str}. "
            f"System is operating in degraded mode with reduced functionality."
        )
