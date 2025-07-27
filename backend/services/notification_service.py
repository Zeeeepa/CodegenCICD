"""
Notification service for CodegenCICD Dashboard
"""
import asyncio
from typing import Dict, Any, List, Optional
from enum import Enum
import structlog

from .base_service import BaseService
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class NotificationType(Enum):
    """Types of notifications"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    AGENT_RUN_COMPLETED = "agent_run_completed"
    VALIDATION_COMPLETED = "validation_completed"
    PR_CREATED = "pr_created"
    PR_MERGED = "pr_merged"


class NotificationChannel(Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    IN_APP = "in_app"


class Notification:
    """Represents a notification to be sent"""
    
    def __init__(self, 
                 notification_type: NotificationType,
                 title: str,
                 message: str,
                 recipient: str,
                 channels: List[NotificationChannel],
                 metadata: Optional[Dict[str, Any]] = None):
        self.notification_type = notification_type
        self.title = title
        self.message = message
        self.recipient = recipient
        self.channels = channels
        self.metadata = metadata or {}
        self.created_at = self._get_timestamp()
        self.sent_at: Optional[str] = None
        self.delivery_status: Dict[str, str] = {}
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"


class NotificationService(BaseService):
    """Service for sending notifications through various channels"""
    
    def __init__(self):
        super().__init__("notification_service")
        self._notification_queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._email_enabled = False
        self._webhook_enabled = False
        self._slack_enabled = False
    
    async def _initialize_service(self) -> None:
        """Initialize notification service"""
        # Check which notification channels are enabled
        self._email_enabled = settings.is_feature_enabled("email_notifications")
        self._webhook_enabled = bool(settings.webhook_url)
        self._slack_enabled = bool(getattr(settings, 'slack_webhook_url', None))
        
        # Start notification worker
        if any([self._email_enabled, self._webhook_enabled, self._slack_enabled]):
            self._worker_task = asyncio.create_task(self._notification_worker())
            self.logger.info("Notification service initialized",
                           email_enabled=self._email_enabled,
                           webhook_enabled=self._webhook_enabled,
                           slack_enabled=self._slack_enabled)
        else:
            self.logger.info("Notification service initialized (all channels disabled)")
    
    async def _close_service(self) -> None:
        """Close notification service"""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
    
    async def send_notification(self, notification: Notification) -> bool:
        """Queue a notification for sending"""
        try:
            await self._notification_queue.put(notification)
            self.logger.debug("Notification queued",
                            type=notification.notification_type.value,
                            recipient=notification.recipient,
                            channels=[c.value for c in notification.channels])
            return True
        except Exception as e:
            self.logger.error("Failed to queue notification", error=str(e))
            return False
    
    async def send_agent_run_notification(self, 
                                        project_name: str,
                                        agent_run_id: str,
                                        status: str,
                                        recipient: str,
                                        pr_url: Optional[str] = None) -> bool:
        """Send agent run completion notification"""
        if status == "completed":
            title = f"Agent Run Completed - {project_name}"
            message = f"Agent run {agent_run_id} has completed successfully."
            if pr_url:
                message += f" PR created: {pr_url}"
            notification_type = NotificationType.AGENT_RUN_COMPLETED
        else:
            title = f"Agent Run Failed - {project_name}"
            message = f"Agent run {agent_run_id} has failed."
            notification_type = NotificationType.ERROR
        
        notification = Notification(
            notification_type=notification_type,
            title=title,
            message=message,
            recipient=recipient,
            channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
            metadata={
                "project_name": project_name,
                "agent_run_id": agent_run_id,
                "status": status,
                "pr_url": pr_url
            }
        )
        
        return await self.send_notification(notification)
    
    async def send_validation_notification(self,
                                         project_name: str,
                                         pr_number: int,
                                         validation_status: str,
                                         overall_score: float,
                                         recipient: str,
                                         auto_merged: bool = False) -> bool:
        """Send validation completion notification"""
        if validation_status == "completed":
            if auto_merged:
                title = f"PR Auto-merged - {project_name} #{pr_number}"
                message = f"PR #{pr_number} passed validation (score: {overall_score:.1f}%) and was automatically merged."
                notification_type = NotificationType.SUCCESS
            else:
                title = f"Validation Completed - {project_name} #{pr_number}"
                message = f"PR #{pr_number} validation completed with score: {overall_score:.1f}%"
                notification_type = NotificationType.VALIDATION_COMPLETED
        else:
            title = f"Validation Failed - {project_name} #{pr_number}"
            message = f"PR #{pr_number} validation failed."
            notification_type = NotificationType.ERROR
        
        notification = Notification(
            notification_type=notification_type,
            title=title,
            message=message,
            recipient=recipient,
            channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
            metadata={
                "project_name": project_name,
                "pr_number": pr_number,
                "validation_status": validation_status,
                "overall_score": overall_score,
                "auto_merged": auto_merged
            }
        )
        
        return await self.send_notification(notification)
    
    async def send_pr_notification(self,
                                 project_name: str,
                                 pr_number: int,
                                 pr_url: str,
                                 action: str,
                                 recipient: str) -> bool:
        """Send PR-related notification"""
        if action == "created":
            title = f"PR Created - {project_name} #{pr_number}"
            message = f"New PR #{pr_number} has been created and validation pipeline started."
            notification_type = NotificationType.PR_CREATED
        elif action == "merged":
            title = f"PR Merged - {project_name} #{pr_number}"
            message = f"PR #{pr_number} has been successfully merged."
            notification_type = NotificationType.PR_MERGED
        else:
            title = f"PR Updated - {project_name} #{pr_number}"
            message = f"PR #{pr_number} has been updated."
            notification_type = NotificationType.INFO
        
        notification = Notification(
            notification_type=notification_type,
            title=title,
            message=message,
            recipient=recipient,
            channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
            metadata={
                "project_name": project_name,
                "pr_number": pr_number,
                "pr_url": pr_url,
                "action": action
            }
        )
        
        return await self.send_notification(notification)
    
    async def _notification_worker(self) -> None:
        """Background worker to process notification queue"""
        while True:
            try:
                # Get notification from queue
                notification = await self._notification_queue.get()
                
                # Process notification through enabled channels
                for channel in notification.channels:
                    try:
                        success = await self._send_through_channel(notification, channel)
                        notification.delivery_status[channel.value] = "sent" if success else "failed"
                    except Exception as e:
                        self.logger.error("Failed to send notification through channel",
                                        channel=channel.value,
                                        error=str(e))
                        notification.delivery_status[channel.value] = "error"
                
                notification.sent_at = notification._get_timestamp()
                
                # Mark task as done
                self._notification_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Notification worker error", error=str(e))
    
    async def _send_through_channel(self, notification: Notification, 
                                  channel: NotificationChannel) -> bool:
        """Send notification through specific channel"""
        if channel == NotificationChannel.EMAIL and self._email_enabled:
            return await self._send_email(notification)
        elif channel == NotificationChannel.WEBHOOK and self._webhook_enabled:
            return await self._send_webhook(notification)
        elif channel == NotificationChannel.SLACK and self._slack_enabled:
            return await self._send_slack(notification)
        elif channel == NotificationChannel.IN_APP:
            return await self._send_in_app(notification)
        else:
            self.logger.debug("Notification channel disabled or not configured",
                            channel=channel.value)
            return False
    
    async def _send_email(self, notification: Notification) -> bool:
        """Send email notification (placeholder implementation)"""
        # TODO: Implement email sending with SMTP
        self.logger.info("Email notification sent (placeholder)",
                        recipient=notification.recipient,
                        title=notification.title)
        return True
    
    async def _send_webhook(self, notification: Notification) -> bool:
        """Send webhook notification"""
        # TODO: Implement webhook sending with HTTP client
        self.logger.info("Webhook notification sent (placeholder)",
                        recipient=notification.recipient,
                        title=notification.title)
        return True
    
    async def _send_slack(self, notification: Notification) -> bool:
        """Send Slack notification"""
        # TODO: Implement Slack webhook sending
        self.logger.info("Slack notification sent (placeholder)",
                        recipient=notification.recipient,
                        title=notification.title)
        return True
    
    async def _send_in_app(self, notification: Notification) -> bool:
        """Send in-app notification (store in database)"""
        # TODO: Store notification in database for in-app display
        self.logger.info("In-app notification stored (placeholder)",
                        recipient=notification.recipient,
                        title=notification.title)
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for notification service"""
        base_health = await super().health_check()
        base_health.update({
            "queue_size": self._notification_queue.qsize(),
            "worker_active": self._worker_task is not None and not self._worker_task.done(),
            "channels": {
                "email_enabled": self._email_enabled,
                "webhook_enabled": self._webhook_enabled,
                "slack_enabled": self._slack_enabled
            }
        })
        return base_health

