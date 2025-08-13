# websocket_manager.py
import asyncio
import json
from typing import Dict, Optional
from fastapi import WebSocket
from uuid import UUID
from core.extends_logger import logger

class ProgressManager:
    """Manages OCR progress tracking and WebSocket connections"""
    
    async def update_progress(self, websocket: WebSocket, document_id: str, stage: str, current: int, total: int, message: str = ""):
        """Update progress for a document"""
        progress_data = {
            "document_id": document_id,
            "stage": stage,
            "current": current,
            "total": total,
            "percentage": round((current / total), 1) if total > 0 else 0,
            "message": message,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await self.send_progress(websocket, document_id, progress_data)
    
    async def send_progress(self, websocket: WebSocket, document_id: str, data: Dict):
        """Send progress data through WebSocket"""
        if websocket:
            try:
                await websocket.send_text(json.dumps(data))
                logger.debug(f"Progress sent for document {document_id}: {data['percentage']}%")
            except Exception as e:
                logger.error(f"Error sending progress for document {document_id}: {e}")
                await websocket.close()
    
    async def complete_progress(self, websocket: WebSocket, document_id: str, success: bool = True, message: str = ""):
        """Mark progress as complete"""
        progress_data = {
            "document_id": document_id,
            "stage": "completed" if success else "failed",
            "current": 100,
            "total": 100,
            "percentage": 100,
            "message": message,
            "completed": True,
            "success": success,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await self.send_progress(websocket, document_id, progress_data)

# Global progress manager instance
progress_manager = ProgressManager()