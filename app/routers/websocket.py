"""WebSocket routes for real-time updates"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.websocket_manager import ws_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time progress updates
    
    Args:
        client_id: Unique identifier for the client connection
    """
    await ws_manager.connect(websocket, client_id)
    
    try:
        # Keep the connection alive and listen for messages
        while True:
            # Wait for any message from client (can be used for heartbeat)
            data = await websocket.receive_text()
            
            # Echo back to confirm connection is alive
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        ws_manager.disconnect(client_id)

