"""
Webhook support and event handling for Codegen API client
"""
import hmac
import hashlib
import json
import asyncio
from typing import Dict, Any, Optional, Callable, List, Union
from datetime import datetime
from dataclasses import dataclass
import structlog
from .models import WebhookEvent, AgentRunResponse, SourceType, MessageType
from .exceptions import WebhookError

logger = structlog.get_logger(__name__)


@dataclass
class WebhookConfig:
    """Configuration for webhook handling"""
    secret: Optional[str] = None
    verify_signatures: bool = True
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    allowed_events: Optional[List[str]] = None
    max_payload_size: int = 1024 * 1024  # 1MB


class WebhookHandler:
    """Handles webhook events with registration and processing"""
    
    def __init__(self, config: Optional[WebhookConfig] = None):
        self.config = config or WebhookConfig()
        self._handlers: Dict[str, List[Callable]] = {}
        self._middleware: List[Callable] = []
        self._stats = {
            'total_events': 0,
            'successful_events': 0,
            'failed_events': 0,
            'events_by_type': {},
            'handler_errors': {}
        }
        
        logger.info("Webhook handler initialized", config=self.config.__dict__)
    
    def register_handler(self, event_type: str, handler: Callable[[WebhookEvent], None]):
        """Register a handler for specific webhook events"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        logger.info("Webhook handler registered", event_type=event_type, handler=handler.__name__)
    
    def register_middleware(self, middleware: Callable[[WebhookEvent], WebhookEvent]):
        """Register middleware that processes all webhook events"""
        self._middleware.append(middleware)
        logger.info("Webhook middleware registered", middleware=middleware.__name__)
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature using HMAC-SHA256"""
        if not self.config.secret:
            logger.warning("Webhook secret not configured, skipping signature verification")
            return True
        
        if not signature:
            logger.error("No signature provided for webhook verification")
            return False
        
        # GitHub-style signature format: sha256=<hash>
        if signature.startswith('sha256='):
            signature = signature[7:]
        
        expected_signature = hmac.new(
            self.config.secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        is_valid = hmac.compare_digest(expected_signature, signature)
        
        if not is_valid:
            logger.error("Webhook signature verification failed")
        
        return is_valid
    
    def validate_payload(self, payload: Dict[str, Any]) -> bool:
        """Validate webhook payload structure and content"""
        # Check payload size
        payload_size = len(json.dumps(payload).encode('utf-8'))
        if payload_size > self.config.max_payload_size:
            logger.error("Webhook payload too large", size=payload_size, max_size=self.config.max_payload_size)
            return False
        
        # Check required fields
        required_fields = ['event_type', 'timestamp', 'data']
        for field in required_fields:
            if field not in payload:
                logger.error("Missing required field in webhook payload", field=field)
                return False
        
        # Check if event type is allowed
        if self.config.allowed_events and payload['event_type'] not in self.config.allowed_events:
            logger.warning("Event type not allowed", event_type=payload['event_type'])
            return False
        
        return True
    
    async def handle_webhook(self, 
                           payload: Union[Dict[str, Any], bytes, str],
                           signature: Optional[str] = None) -> Dict[str, Any]:
        """Process incoming webhook payload"""
        try:
            # Parse payload if needed
            if isinstance(payload, bytes):
                payload_bytes = payload
                payload_dict = json.loads(payload.decode('utf-8'))
            elif isinstance(payload, str):
                payload_bytes = payload.encode('utf-8')
                payload_dict = json.loads(payload)
            else:
                payload_dict = payload
                payload_bytes = json.dumps(payload).encode('utf-8')
            
            # Verify signature if required
            if self.config.verify_signatures and signature:
                if not self.verify_signature(payload_bytes, signature):
                    raise WebhookError("Signature verification failed")
            
            # Validate payload
            if not self.validate_payload(payload_dict):
                raise WebhookError("Payload validation failed")
            
            # Create webhook event
            webhook_event = WebhookEvent(
                event_type=payload_dict['event_type'],
                timestamp=datetime.fromisoformat(payload_dict['timestamp'].replace('Z', '+00:00')),
                data=payload_dict['data'],
                signature=signature
            )
            
            # Apply middleware
            for middleware in self._middleware:
                try:
                    webhook_event = middleware(webhook_event)
                except Exception as e:
                    logger.error("Middleware error", middleware=middleware.__name__, error=str(e))
                    # Continue processing even if middleware fails
            
            # Update stats
            self._stats['total_events'] += 1
            event_type = webhook_event.event_type
            self._stats['events_by_type'][event_type] = self._stats['events_by_type'].get(event_type, 0) + 1
            
            # Process handlers
            handlers = self._handlers.get(event_type, [])
            if not handlers:
                logger.warning("No handlers registered for event type", event_type=event_type)
                return {
                    'status': 'no_handlers',
                    'event_type': event_type,
                    'timestamp': webhook_event.timestamp.isoformat()
                }
            
            # Execute handlers
            handler_results = []
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(webhook_event)
                    else:
                        result = handler(webhook_event)
                    
                    handler_results.append({
                        'handler': handler.__name__,
                        'status': 'success',
                        'result': result
                    })
                    
                except Exception as e:
                    error_key = f"{event_type}.{handler.__name__}"
                    self._stats['handler_errors'][error_key] = self._stats['handler_errors'].get(error_key, 0) + 1
                    
                    handler_results.append({
                        'handler': handler.__name__,
                        'status': 'error',
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                    
                    logger.error("Handler error", 
                               handler=handler.__name__, 
                               event_type=event_type,
                               error=str(e))
            
            # Determine overall success
            successful_handlers = sum(1 for r in handler_results if r['status'] == 'success')
            if successful_handlers > 0:
                self._stats['successful_events'] += 1
            else:
                self._stats['failed_events'] += 1
            
            logger.info("Webhook processed", 
                       event_type=event_type,
                       handlers_executed=len(handler_results),
                       successful_handlers=successful_handlers)
            
            return {
                'status': 'processed',
                'event_type': event_type,
                'timestamp': webhook_event.timestamp.isoformat(),
                'handlers_executed': len(handler_results),
                'successful_handlers': successful_handlers,
                'handler_results': handler_results
            }
            
        except Exception as e:
            self._stats['failed_events'] += 1
            logger.error("Webhook processing failed", error=str(e), error_type=type(e).__name__)
            
            return {
                'status': 'error',
                'error': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get webhook processing statistics"""
        return {
            'total_events': self._stats['total_events'],
            'successful_events': self._stats['successful_events'],
            'failed_events': self._stats['failed_events'],
            'success_rate': (self._stats['successful_events'] / max(1, self._stats['total_events'])) * 100,
            'events_by_type': self._stats['events_by_type'],
            'handler_errors': self._stats['handler_errors'],
            'registered_handlers': {
                event_type: len(handlers) for event_type, handlers in self._handlers.items()
            },
            'middleware_count': len(self._middleware)
        }
    
    def list_handlers(self) -> Dict[str, List[str]]:
        """List all registered handlers by event type"""
        return {
            event_type: [handler.__name__ for handler in handlers]
            for event_type, handlers in self._handlers.items()
        }


# Predefined event handlers for common scenarios
class DefaultHandlers:
    """Default webhook handlers for common Codegen events"""
    
    @staticmethod
    async def agent_run_completed(event: WebhookEvent):
        """Handle agent run completion events"""
        logger.info("Agent run completed", 
                   agent_run_id=event.data.get('id'),
                   status=event.data.get('status'),
                   result=event.data.get('result', '')[:100])  # Truncate result for logging
    
    @staticmethod
    async def agent_run_failed(event: WebhookEvent):
        """Handle agent run failure events"""
        logger.error("Agent run failed",
                    agent_run_id=event.data.get('id'),
                    error=event.data.get('error'),
                    status=event.data.get('status'))
    
    @staticmethod
    async def pr_created(event: WebhookEvent):
        """Handle PR creation events"""
        pr_data = event.data.get('github_pull_request', {})
        logger.info("PR created by agent",
                   pr_id=pr_data.get('id'),
                   pr_title=pr_data.get('title'),
                   pr_url=pr_data.get('url'))
    
    @staticmethod
    async def error_occurred(event: WebhookEvent):
        """Handle error events"""
        logger.error("Agent error occurred",
                    error_type=event.data.get('error_type'),
                    error_message=event.data.get('error_message'),
                    agent_run_id=event.data.get('agent_run_id'))


class WebhookMiddleware:
    """Common webhook middleware functions"""
    
    @staticmethod
    def logging_middleware(event: WebhookEvent) -> WebhookEvent:
        """Log all webhook events"""
        logger.info("Webhook event received",
                   event_type=event.event_type,
                   timestamp=event.timestamp.isoformat(),
                   data_keys=list(event.data.keys()) if event.data else [])
        return event
    
    @staticmethod
    def validation_middleware(event: WebhookEvent) -> WebhookEvent:
        """Validate webhook event data"""
        # Add custom validation logic here
        if not event.data:
            raise WebhookError("Event data is empty")
        
        return event
    
    @staticmethod
    def enrichment_middleware(event: WebhookEvent) -> WebhookEvent:
        """Enrich webhook events with additional context"""
        # Add processing timestamp
        event.data['processed_at'] = datetime.utcnow().isoformat()
        
        # Add event metadata
        event.data['_metadata'] = {
            'handler_version': '2.0',
            'processing_node': 'codegen-cicd'
        }
        
        return event


class WebhookServer:
    """Simple webhook server for testing and development"""
    
    def __init__(self, handler: WebhookHandler, host: str = '0.0.0.0', port: int = 8080):
        self.handler = handler
        self.host = host
        self.port = port
        self._server = None
    
    async def handle_request(self, request):
        """Handle incoming HTTP webhook requests"""
        try:
            # Extract signature from headers
            signature = request.headers.get('X-Hub-Signature-256') or request.headers.get('X-Signature')
            
            # Get request body
            body = await request.read()
            
            # Process webhook
            result = await self.handler.handle_webhook(body, signature)
            
            # Return appropriate response
            if result['status'] == 'processed':
                return {'status': 200, 'body': json.dumps(result)}
            else:
                return {'status': 400, 'body': json.dumps(result)}
                
        except Exception as e:
            logger.error("Webhook server error", error=str(e))
            return {
                'status': 500,
                'body': json.dumps({
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                })
            }
    
    async def start(self):
        """Start the webhook server"""
        logger.info("Starting webhook server", host=self.host, port=self.port)
        # Implementation would depend on chosen web framework (aiohttp, FastAPI, etc.)
        # This is a placeholder for the actual server implementation
    
    async def stop(self):
        """Stop the webhook server"""
        logger.info("Stopping webhook server")
        # Implementation for stopping the server


# Utility functions
def create_webhook_handler(config: Optional[Dict[str, Any]] = None) -> WebhookHandler:
    """Create a webhook handler with optional configuration"""
    webhook_config = WebhookConfig()
    
    if config:
        for key, value in config.items():
            if hasattr(webhook_config, key):
                setattr(webhook_config, key, value)
    
    handler = WebhookHandler(webhook_config)
    
    # Register default middleware
    handler.register_middleware(WebhookMiddleware.logging_middleware)
    handler.register_middleware(WebhookMiddleware.validation_middleware)
    
    return handler


def setup_default_handlers(handler: WebhookHandler):
    """Set up default handlers for common events"""
    handler.register_handler('agent_run.completed', DefaultHandlers.agent_run_completed)
    handler.register_handler('agent_run.failed', DefaultHandlers.agent_run_failed)
    handler.register_handler('github.pr.created', DefaultHandlers.pr_created)
    handler.register_handler('error.occurred', DefaultHandlers.error_occurred)


# Example usage and testing utilities
class WebhookTester:
    """Utility for testing webhook handlers"""
    
    def __init__(self, handler: WebhookHandler):
        self.handler = handler
    
    async def send_test_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a test webhook event"""
        test_payload = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        return await self.handler.handle_webhook(test_payload)
    
    async def test_agent_run_completed(self, agent_run_id: int = 123):
        """Test agent run completion webhook"""
        return await self.send_test_event('agent_run.completed', {
            'id': agent_run_id,
            'status': 'completed',
            'result': 'Task completed successfully',
            'github_pull_requests': [
                {
                    'id': 456,
                    'title': 'Fix bug in authentication',
                    'url': 'https://github.com/org/repo/pull/456'
                }
            ]
        })
    
    async def test_agent_run_failed(self, agent_run_id: int = 123):
        """Test agent run failure webhook"""
        return await self.send_test_event('agent_run.failed', {
            'id': agent_run_id,
            'status': 'failed',
            'error': 'Authentication failed',
            'error_type': 'AuthenticationError'
        })


# Global webhook handler instance
default_webhook_handler = create_webhook_handler()
setup_default_handlers(default_webhook_handler)

