"""
WebSocket router for CodegenCICD Dashboard
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import structlog

from backend.services.websocket_service import WebSocketService
from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter()

# Global WebSocket service instance
websocket_service = WebSocketService()


@router.websocket("/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time updates"""
    if not settings.is_feature_enabled("websocket_updates"):
        await websocket.close(code=1000, reason="WebSocket updates disabled")
        return
    
    connection = None
    try:
        # Initialize service if not already done
        if not websocket_service.is_initialized:
            await websocket_service.initialize()
        
        # Accept connection
        connection = await websocket_service.connect(websocket, client_id)
        
        logger.info("WebSocket connection established", client_id=client_id)
        
        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle message
                await websocket_service.handle_client_message(client_id, message)
                
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received from WebSocket client", 
                             client_id=client_id)
                await connection.send_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected", client_id=client_id)
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected during setup", client_id=client_id)
    
    except Exception as e:
        logger.error("WebSocket error", client_id=client_id, error=str(e))
    
    finally:
        # Clean up connection
        if connection:
            await websocket_service.disconnect(client_id)


@router.get("/health")
async def websocket_health():
    """WebSocket service health check"""
    try:
        health = await websocket_service.health_check()
        return health
    except Exception as e:
        logger.error("WebSocket health check failed", error=str(e))
        return {
            "service": "websocket_service",
            "status": "unhealthy",
            "error": str(e)
        }

