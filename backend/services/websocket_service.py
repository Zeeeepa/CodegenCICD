"""
WebSocket service for real-time updates in CodegenCICD Dashboard
"""
import json
import asyncio
from typing import Dict, Any, List, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect
import structlog

from .base_service import BaseService
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class WebSocketConnection:
    """Represents a WebSocket connection with metadata"""
    
    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.subscriptions: Set[str] = set()
        self.metadata: Dict[str, Any] = {}
        self.is_active = True
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message to client, return success status"""
        try:
            await self.websocket.send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.warning("Failed to send WebSocket message", 
                         client_id=self.client_id, error=str(e))
            self.is_active = False
            return False
    
    def subscribe_to_project(self, project_id: str) -> None:
        """Subscribe to project updates"""
        self.subscriptions.add(f"project:{project_id}")
    
    def unsubscribe_from_project(self, project_id: str) -> None:
        """Unsubscribe from project updates"""
        self.subscriptions.discard(f"project:{project_id}")
    
    def is_subscribed_to(self, channel: str) -> bool:
        """Check if connection is subscribed to a channel"""
        return channel in self.subscriptions


class WebSocketService(BaseService):
    """Service for managing WebSocket connections and real-time updates"""
    
    def __init__(self):
        super().__init__("websocket_service")
        self.active_connections: Dict[str, WebSocketConnection] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_interval = 30  # seconds
    
    async def _initialize_service(self) -> None:
        """Initialize WebSocket service"""
        if settings.is_feature_enabled("websocket_updates"):
            # Start heartbeat task
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.logger.info("WebSocket service initialized with heartbeat")
        else:
            self.logger.info("WebSocket service initialized (disabled by config)")
    
    async def _close_service(self) -> None:
        """Close WebSocket service"""
        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        await self.close_all_connections()
    
    async def connect(self, websocket: WebSocket, client_id: str) -> WebSocketConnection:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        connection = WebSocketConnection(websocket, client_id)
        self.active_connections[client_id] = connection
        
        self.logger.info("WebSocket client connected", 
                        client_id=client_id, 
                        total_connections=len(self.active_connections))
        
        # Send welcome message
        await connection.send_message({
            "type": "connection_established",
            "client_id": client_id,
            "timestamp": self._get_timestamp(),
            "features": settings.get_active_features()
        })
        
        return connection
    
    async def disconnect(self, client_id: str) -> None:
        """Disconnect a WebSocket client"""
        if client_id in self.active_connections:
            connection = self.active_connections[client_id]
            connection.is_active = False
            del self.active_connections[client_id]
            
            self.logger.info("WebSocket client disconnected", 
                           client_id=client_id,
                           total_connections=len(self.active_connections))
    
    async def handle_client_message(self, client_id: str, message: Dict[str, Any]) -> None:
        """Handle incoming message from WebSocket client"""
        connection = self.active_connections.get(client_id)
        if not connection:
            return
        
        message_type = message.get("type")
        
        if message_type == "subscribe_project":
            project_id = message.get("project_id")
            if project_id:
                connection.subscribe_to_project(project_id)
                await connection.send_message({
                    "type": "subscription_confirmed",
                    "channel": f"project:{project_id}",
                    "timestamp": self._get_timestamp()
                })
        
        elif message_type == "unsubscribe_project":
            project_id = message.get("project_id")
            if project_id:
                connection.unsubscribe_from_project(project_id)
                await connection.send_message({
                    "type": "unsubscription_confirmed",
                    "channel": f"project:{project_id}",
                    "timestamp": self._get_timestamp()
                })
        
        elif message_type == "ping":
            await connection.send_message({
                "type": "pong",
                "timestamp": self._get_timestamp()
            })
        
        else:
            self.logger.warning("Unknown WebSocket message type", 
                              client_id=client_id, message_type=message_type)
    
    async def broadcast_to_project(self, project_id: str, message: Dict[str, Any]) -> int:
        """Broadcast message to all clients subscribed to a project"""
        channel = f"project:{project_id}"
        sent_count = 0
        
        # Add project context to message
        message.update({
            "project_id": project_id,
            "timestamp": self._get_timestamp()
        })
        
        for client_id, connection in list(self.active_connections.items()):
            if connection.is_subscribed_to(channel) and connection.is_active:
                success = await connection.send_message(message)
                if success:
                    sent_count += 1
                else:
                    # Remove inactive connection
                    await self.disconnect(client_id)
        
        self.logger.debug("Broadcasted message to project subscribers",
                         project_id=project_id, 
                         message_type=message.get("type"),
                         sent_count=sent_count)
        
        return sent_count
    
    async def send_agent_run_update(self, project_id: str, agent_run_id: str, 
                                   status: str, data: Dict[str, Any]) -> int:
        """Send agent run update to subscribed clients"""
        message = {
            "type": "agent_run_update",
            "agent_run_id": agent_run_id,
            "status": status,
            "data": data
        }
        return await self.broadcast_to_project(project_id, message)
    
    async def send_validation_update(self, project_id: str, validation_run_id: str,
                                   step_index: int, step_data: Dict[str, Any],
                                   overall_status: str) -> int:
        """Send validation pipeline update to subscribed clients"""
        message = {
            "type": "validation_update",
            "validation_run_id": validation_run_id,
            "step_index": step_index,
            "step": step_data,
            "overall_status": overall_status
        }
        return await self.broadcast_to_project(project_id, message)
    
    async def send_pr_notification(self, project_id: str, pr_url: str, 
                                  pr_number: int, action: str) -> int:
        """Send PR notification to subscribed clients"""
        message = {
            "type": "pr_notification",
            "pr_url": pr_url,
            "pr_number": pr_number,
            "action": action
        }
        return await self.broadcast_to_project(project_id, message)
    
    async def close_all_connections(self) -> None:
        """Close all active WebSocket connections"""
        for client_id in list(self.active_connections.keys()):
            await self.disconnect(client_id)
    
    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat to detect dead connections"""
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                
                # Send heartbeat to all connections
                dead_connections = []
                for client_id, connection in self.active_connections.items():
                    success = await connection.send_message({
                        "type": "heartbeat",
                        "timestamp": self._get_timestamp()
                    })
                    if not success:
                        dead_connections.append(client_id)
                
                # Remove dead connections
                for client_id in dead_connections:
                    await self.disconnect(client_id)
                
                if dead_connections:
                    self.logger.info("Removed dead WebSocket connections",
                                   count=len(dead_connections))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Heartbeat loop error", error=str(e))
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for WebSocket service"""
        base_health = await super().health_check()
        base_health.update({
            "active_connections": len(self.active_connections),
            "heartbeat_active": self._heartbeat_task is not None and not self._heartbeat_task.done(),
            "websocket_enabled": settings.is_feature_enabled("websocket_updates")
        })
        return base_health

