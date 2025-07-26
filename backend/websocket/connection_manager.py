"""
WebSocket connection manager for real-time updates
"""
import asyncio
import json
import structlog
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Active connections: client_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Project subscriptions: project_id -> set of client_ids
        self.project_subscriptions: Dict[int, Set[str]] = {}
        
        # Agent run subscriptions: agent_run_id -> set of client_ids
        self.agent_run_subscriptions: Dict[int, Set[str]] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Heartbeat tracking
        self.last_heartbeat: Dict[str, datetime] = {}
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_stale_connections())
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        self.active_connections[client_id] = websocket
        self.connection_metadata[client_id] = {
            "connected_at": datetime.utcnow(),
            "user_agent": websocket.headers.get("user-agent", ""),
            "ip_address": websocket.client.host if websocket.client else "unknown"
        }
        self.last_heartbeat[client_id] = datetime.utcnow()
        
        logger.info(
            "WebSocket connection established",
            client_id=client_id,
            total_connections=len(self.active_connections)
        )
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat()
        }, client_id)
    
    def disconnect(self, client_id: str):
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        if client_id in self.connection_metadata:
            del self.connection_metadata[client_id]
        
        if client_id in self.last_heartbeat:
            del self.last_heartbeat[client_id]
        
        # Remove from all subscriptions
        self._remove_from_all_subscriptions(client_id)
        
        logger.info(
            "WebSocket connection closed",
            client_id=client_id,
            total_connections=len(self.active_connections)
        )
    
    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(
                    "Failed to send personal message",
                    client_id=client_id,
                    error=str(e)
                )
                # Remove stale connection
                self.disconnect(client_id)
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients"""
        if not self.active_connections:
            return
        
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(
                    "Failed to broadcast message",
                    client_id=client_id,
                    error=str(e)
                )
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def subscribe_to_project(self, client_id: str, project_id: int):
        """Subscribe a client to project updates"""
        if project_id not in self.project_subscriptions:
            self.project_subscriptions[project_id] = set()
        
        self.project_subscriptions[project_id].add(client_id)
        
        logger.info(
            "Client subscribed to project",
            client_id=client_id,
            project_id=project_id
        )
        
        # Send confirmation
        await self.send_personal_message({
            "type": "subscription_confirmed",
            "subscription_type": "project",
            "project_id": project_id,
            "timestamp": datetime.utcnow().isoformat()
        }, client_id)
    
    async def unsubscribe_from_project(self, client_id: str, project_id: int):
        """Unsubscribe a client from project updates"""
        if project_id in self.project_subscriptions:
            self.project_subscriptions[project_id].discard(client_id)
            
            # Clean up empty subscription sets
            if not self.project_subscriptions[project_id]:
                del self.project_subscriptions[project_id]
        
        logger.info(
            "Client unsubscribed from project",
            client_id=client_id,
            project_id=project_id
        )
    
    async def subscribe_to_agent_run(self, client_id: str, agent_run_id: int):
        """Subscribe a client to agent run updates"""
        if agent_run_id not in self.agent_run_subscriptions:
            self.agent_run_subscriptions[agent_run_id] = set()
        
        self.agent_run_subscriptions[agent_run_id].add(client_id)
        
        logger.info(
            "Client subscribed to agent run",
            client_id=client_id,
            agent_run_id=agent_run_id
        )
        
        # Send confirmation
        await self.send_personal_message({
            "type": "subscription_confirmed",
            "subscription_type": "agent_run",
            "agent_run_id": agent_run_id,
            "timestamp": datetime.utcnow().isoformat()
        }, client_id)
    
    async def unsubscribe_from_agent_run(self, client_id: str, agent_run_id: int):
        """Unsubscribe a client from agent run updates"""
        if agent_run_id in self.agent_run_subscriptions:
            self.agent_run_subscriptions[agent_run_id].discard(client_id)
            
            # Clean up empty subscription sets
            if not self.agent_run_subscriptions[agent_run_id]:
                del self.agent_run_subscriptions[agent_run_id]
        
        logger.info(
            "Client unsubscribed from agent run",
            client_id=client_id,
            agent_run_id=agent_run_id
        )
    
    async def broadcast_to_project(self, project_id: int, message: Dict[str, Any]):
        """Broadcast a message to all clients subscribed to a project"""
        if project_id not in self.project_subscriptions:
            return
        
        subscribers = self.project_subscriptions[project_id].copy()
        disconnected_clients = []
        
        for client_id in subscribers:
            if client_id in self.active_connections:
                try:
                    websocket = self.active_connections[client_id]
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(
                        "Failed to send project message",
                        client_id=client_id,
                        project_id=project_id,
                        error=str(e)
                    )
                    disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def broadcast_to_agent_run(self, agent_run_id: int, message: Dict[str, Any]):
        """Broadcast a message to all clients subscribed to an agent run"""
        if agent_run_id not in self.agent_run_subscriptions:
            return
        
        subscribers = self.agent_run_subscriptions[agent_run_id].copy()
        disconnected_clients = []
        
        for client_id in subscribers:
            if client_id in self.active_connections:
                try:
                    websocket = self.active_connections[client_id]
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(
                        "Failed to send agent run message",
                        client_id=client_id,
                        agent_run_id=agent_run_id,
                        error=str(e)
                    )
                    disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def handle_message(self, client_id: str, message: Dict[str, Any]):
        """Handle incoming WebSocket message from client"""
        message_type = message.get("type")
        
        try:
            if message_type == "ping":
                # Update heartbeat
                self.last_heartbeat[client_id] = datetime.utcnow()
                await self.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }, client_id)
            
            elif message_type == "subscribe_project":
                project_id = message.get("project_id")
                if project_id:
                    await self.subscribe_to_project(client_id, project_id)
            
            elif message_type == "unsubscribe_project":
                project_id = message.get("project_id")
                if project_id:
                    await self.unsubscribe_from_project(client_id, project_id)
            
            elif message_type == "subscribe_agent_run":
                agent_run_id = message.get("agent_run_id")
                if agent_run_id:
                    await self.subscribe_to_agent_run(client_id, agent_run_id)
            
            elif message_type == "unsubscribe_agent_run":
                agent_run_id = message.get("agent_run_id")
                if agent_run_id:
                    await self.unsubscribe_from_agent_run(client_id, agent_run_id)
            
            else:
                logger.warning(
                    "Unknown WebSocket message type",
                    client_id=client_id,
                    message_type=message_type
                )
        
        except Exception as e:
            logger.error(
                "Error handling WebSocket message",
                client_id=client_id,
                message_type=message_type,
                error=str(e)
            )
            
            await self.send_personal_message({
                "type": "error",
                "message": f"Failed to handle message: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }, client_id)
    
    def _remove_from_all_subscriptions(self, client_id: str):
        """Remove client from all subscriptions"""
        # Remove from project subscriptions
        for project_id in list(self.project_subscriptions.keys()):
            self.project_subscriptions[project_id].discard(client_id)
            if not self.project_subscriptions[project_id]:
                del self.project_subscriptions[project_id]
        
        # Remove from agent run subscriptions
        for agent_run_id in list(self.agent_run_subscriptions.keys()):
            self.agent_run_subscriptions[agent_run_id].discard(client_id)
            if not self.agent_run_subscriptions[agent_run_id]:
                del self.agent_run_subscriptions[agent_run_id]
    
    async def _cleanup_stale_connections(self):
        """Periodically clean up stale connections"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                cutoff_time = datetime.utcnow() - timedelta(minutes=5)  # 5 minute timeout
                stale_clients = []
                
                for client_id, last_heartbeat in self.last_heartbeat.items():
                    if last_heartbeat < cutoff_time:
                        stale_clients.append(client_id)
                
                for client_id in stale_clients:
                    logger.info("Cleaning up stale connection", client_id=client_id)
                    self.disconnect(client_id)
                
            except Exception as e:
                logger.error("Error in connection cleanup", error=str(e))
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "project_subscriptions": {
                project_id: len(clients) 
                for project_id, clients in self.project_subscriptions.items()
            },
            "agent_run_subscriptions": {
                agent_run_id: len(clients)
                for agent_run_id, clients in self.agent_run_subscriptions.items()
            },
            "connection_metadata": self.connection_metadata
        }

