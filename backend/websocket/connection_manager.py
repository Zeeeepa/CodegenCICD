"""
WebSocket connection manager for real-time updates
"""
import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Store active connections by client ID
        self.active_connections: Dict[str, WebSocket] = {}
        # Store project subscriptions by project ID
        self.project_subscriptions: Dict[int, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")
    
    def disconnect(self, client_id: str):
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
            # Remove from project subscriptions
            for project_id, subscribers in self.project_subscriptions.items():
                subscribers.discard(client_id)
            
            logger.info(f"WebSocket client disconnected: {client_id}")
    
    async def send_personal_message(self, message: str, client_id: str):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def send_personal_json(self, data: dict, client_id: str):
        """Send JSON data to a specific client"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Error sending JSON to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all connected clients"""
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def broadcast_json(self, data: dict):
        """Broadcast JSON data to all connected clients"""
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Error broadcasting JSON to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    def subscribe_to_project(self, client_id: str, project_id: int):
        """Subscribe a client to project updates"""
        if project_id not in self.project_subscriptions:
            self.project_subscriptions[project_id] = set()
        
        self.project_subscriptions[project_id].add(client_id)
        logger.info(f"Client {client_id} subscribed to project {project_id}")
    
    def unsubscribe_from_project(self, client_id: str, project_id: int):
        """Unsubscribe a client from project updates"""
        if project_id in self.project_subscriptions:
            self.project_subscriptions[project_id].discard(client_id)
            
            # Clean up empty subscriptions
            if not self.project_subscriptions[project_id]:
                del self.project_subscriptions[project_id]
        
        logger.info(f"Client {client_id} unsubscribed from project {project_id}")
    
    async def broadcast_to_project(self, project_id: int, data: dict):
        """Broadcast data to all clients subscribed to a project"""
        if project_id not in self.project_subscriptions:
            return
        
        subscribers = self.project_subscriptions[project_id].copy()
        disconnected_clients = []
        
        for client_id in subscribers:
            if client_id in self.active_connections:
                try:
                    websocket = self.active_connections[client_id]
                    await websocket.send_json({
                        **data,
                        "project_id": project_id,
                        "timestamp": data.get("timestamp") or self._get_timestamp()
                    })
                except Exception as e:
                    logger.error(f"Error sending project update to {client_id}: {e}")
                    disconnected_clients.append(client_id)
            else:
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def handle_client_message(self, client_id: str, message: str):
        """Handle incoming message from a client"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "subscribe_project":
                project_id = data.get("project_id")
                if project_id:
                    self.subscribe_to_project(client_id, project_id)
                    await self.send_personal_json({
                        "type": "subscription_confirmed",
                        "project_id": project_id
                    }, client_id)
            
            elif message_type == "unsubscribe_project":
                project_id = data.get("project_id")
                if project_id:
                    self.unsubscribe_from_project(client_id, project_id)
                    await self.send_personal_json({
                        "type": "unsubscription_confirmed",
                        "project_id": project_id
                    }, client_id)
            
            elif message_type == "ping":
                await self.send_personal_json({
                    "type": "pong",
                    "timestamp": self._get_timestamp()
                }, client_id)
            
            else:
                logger.warning(f"Unknown message type from {client_id}: {message_type}")
        
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from client {client_id}: {message}")
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
    
    def get_connection_stats(self) -> dict:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "project_subscriptions": {
                project_id: len(subscribers)
                for project_id, subscribers in self.project_subscriptions.items()
            }
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"

# Global connection manager instance
connection_manager = ConnectionManager()

