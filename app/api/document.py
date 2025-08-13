from typing import List, Optional
import os
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
from datetime import datetime

from models.models import Document, ProcessingStatus
from services.document_service import DocumentService
from schemas.document import *
from schemas.result import ok, failed
from core.error_handle import MyException
from core.i18n import _
from core import config
from core.extends_logger import logger
from api.auth import login_required
from fastapi import BackgroundTasks
from fastapi import WebSocket, WebSocketDisconnect
import traceback

router = APIRouter()

def get_document_service():
    return DocumentService()

# Document endpoints
@router.put("")
async def save_document(
    document: DocumentView,
    user: dict = Depends(login_required),
    document_service: DocumentService = Depends(get_document_service)
):
    """Create a new document."""
    try:
        document = document_service.save_document(document, user.get("userid"), user.get("token"))
        return ok(document.to_dict())
    except MyException as e:
        logger.error(f"Failed to save document: {e.code} {e.msg}")
        return failed(data=None, msg=e.msg)
    except Exception as e:
        logger.error(f"Failed to save document: {e}")
        return failed(data=None, msg=_("Failed to save document. Please try again later."))

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    user: dict = Depends(login_required),
    document_service: DocumentService = Depends(get_document_service),
):
    """Delete a document (soft delete)."""
    try:
        document_service.delete_document(document_id, user.get("userid"), user.get("token"))
        return ok()
    except MyException as e:
        logger.error(f"Failed to delete document: {e.code} {e.msg}")
        return failed(data=None, msg=e.msg)
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        return failed(data=None, msg=_("Failed to delete document. Please try again later."))

@router.post("")
async def list_documents(
    condition: DocumentList,
    user: dict = Depends(login_required),
    document_service: DocumentService = Depends(get_document_service),
):
    """List all documents."""
    try:
        documents, total = document_service.list_documents(condition, user.get("userid"))
        return ok({
            "documents": [document.to_dict() for document in documents],
            "total": total
        })
    except MyException as e:
        logger.error(f"Failed to list documents: {e.code} {e.msg}")
        return failed(data=None, msg=e.msg)
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        return failed(data=None, msg=_("Failed to list documents. Please try again later."))

@router.get("/find/{document_id}")
async def get_document(
    document_id: UUID,
    user: dict = Depends(login_required),
    document_service: DocumentService = Depends(get_document_service),
):
    """Get a specific document by ID."""
    try:
        document = document_service.get_document_by_id(document_id)
        if not document:
            return failed(data=None, msg=_("Document not found"))
        return ok(document.to_dict())
    except MyException as e:
        logger.error(f"Failed to get document: {e.code} {e.msg}")
        return failed(data=None, msg=e.msg)
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        return failed(data=None, msg=_("Failed to get document. Please try again later."))

@router.post("/upload")
async def upload_doc(
    file: UploadFile = File(..., description="Law document file to upload"),
    user: dict = Depends(login_required),
    document_service: DocumentService = Depends(get_document_service),
):
    """Upload law document."""
    try:
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        extension = file.filename.split(".")[-1]
        new_filename = f"{uuid4()}.{extension}"
        document_path = os.path.join(config.UPLOAD_FOLDER, year, month, day, new_filename)
        os.makedirs(os.path.dirname(document_path), exist_ok=True)
        with open(document_path, "wb") as f:
            f.write(file.file.read())

        relative_path = document_path.replace(config.UPLOAD_FOLDER, '')

        document = Document(
            filename=file.filename,
            file_size=file.size,
            file_type=extension,
            file_path=relative_path.strip('/'),
            status=ProcessingStatus.pending,
            created_at=now,
            updated_at=now,
            created_by=user.get("userid"),
            updated_by=user.get("userid"),
        )

        document: Document = document_service.save_document(document, user.get("userid"))
        return ok(document.to_dict()) 
    except MyException as e:
        logger.error(f"Failed to upload document: {e.code} {e.msg}")
        return failed(data=None, msg=e.msg)
    except Exception as e:
        logger.error(f"Failed to upload document: {e}")
        traceback.print_exc()
        return failed(data=None, msg=_("Failed to upload document. Please try again later."))

@router.post("/parse/{document_id}")
async def parse_doc_async(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    user: dict = Depends(login_required),
    document_service: DocumentService = Depends(get_document_service),
):
    """Parse law document with real-time progress updates."""
    try:
        # Start the parsing process in the background
        background_tasks.add_task(
            document_service.parse_doc_with_progress,
            document_id,
            user.get("userid")
        )
        
        # Return immediately to allow WebSocket connection
        return ok({
            "message": "OCR processing started",
            "document_id": str(document_id),
            "websocket_url": f"/ws/progress/{document_id}"
        })
        
    except MyException as e:
        logger.error(f"Failed to start document parsing: {e.code} {e.msg}")
        return failed(data=None, msg=e.msg)
    except Exception as e:
        logger.error(f"Failed to start document parsing: {e}")
        traceback.print_exc()
        return failed(data=None, msg=_("Failed to start document parsing. Please try again later."))

@router.websocket("/parse_progress")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # Keep connection alive
        while True:
                data = None
                try:
                    # Wait for messages (ping/pong to keep connection alive)
                    data = await websocket.receive_json()
                    if not data:
                        continue

                    await websocket.send_text(json.dumps({"message": "progress", "data": data}))
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"WebSocket error for document {data}: {e}")   
                    break
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")

    return current_app
    
@router.post("/download_parse_result/{document_id}")
async def download_parse_result(
    document_id: UUID,
    user: dict = Depends(login_required),
    document_service: DocumentService = Depends(get_document_service),
):
    """Download parse result."""
    try:
        export_result_path: str = document_service.export_parse_result(document_id, user.get("userid"))
        export_result_path = export_result_path.replace(config.DATA_DIR, '')
        return ok(export_result_path.strip('/')) 
    except MyException as e:
        logger.error(f"Failed to download parse result: {e.code} {e.msg}")
        return failed(data=None, msg=e.msg)
    except Exception as e:
        logger.error(f"Failed to download parse result: {e}")
        traceback.print_exc()
        return failed(data=None, msg=_("Failed to download parse result. Please try again later."))

@router.post("/search")
async def search_documents(
    search_query: str = Query(..., description="Search query for documents and OCR results"),
    limit: int = Query(50, description="Maximum number of results to return"),
    offset: int = Query(0, description="Number of results to skip for pagination"),
    user: dict = Depends(login_required),
    document_service: DocumentService = Depends(get_document_service),
):
    """Search documents by text content, filename, or OCR results."""
    try:
        documents, total = document_service.search_documents(
            search_query, user.get("userid"), limit, offset
        )
        return ok({
            "documents": [document.to_dict() for document in documents],
            "total": total,
            "limit": limit,
            "offset": offset
        })
    except MyException as e:
        logger.error(f"Failed to search documents: {e.code} {e.msg}")
        return failed(data=None, msg=e.msg)
    except Exception as e:
        logger.error(f"Failed to search documents: {e}")
        traceback.print_exc()
        return failed(data=None, msg=_("Failed to search documents. Please try again later."))

@router.get("/statistics")
async def get_ocr_statistics(
    user: dict = Depends(login_required),
    document_service: DocumentService = Depends(get_document_service),
):
    """Get OCR processing statistics for the current user."""
    try:
        statistics = document_service.get_ocr_statistics(user.get("userid"))
        return ok(statistics)
    except MyException as e:
        logger.error(f"Failed to get OCR statistics: {e.code} {e.msg}")
        return failed(data=None, msg=e.msg)
    except Exception as e:
        logger.error(f"Failed to get OCR statistics: {e}")
        traceback.print_exc()
        return failed(data=None, msg=_("Failed to get OCR statistics. Please try again later."))
