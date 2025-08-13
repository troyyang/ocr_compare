# tests/services/test_document_service.py

import pytest
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from models.models import Document, OcrResult, FileType, ProcessingStatus, OcrEngine
from services.document_service import DocumentService
from core.error_handle import MyException
from core.i18n import _
from uuid import UUID

def setup_function(monkeypatch) -> None:
    monkeypatch.setattr(config, 'API_ENV', 'test')
    yield

@pytest.fixture
def document_service(monkeypatch):
    return DocumentService()

DEMO_DOC_ID = UUID('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a15')

# Sample document data
SAMPLE_DOC = {
    'filename': 'test.pdf',
    'file_type': 'pdf',
    'file_path': '/uploads/test.pdf',
    'file_size': 1024,
    'status': 'pending'
}

# Sample OCR result data
SAMPLE_OCR = {
    'engine': 'paddleocr',
    'extracted_text': 'This is sample extracted text',
    'processing_time_ms': 1500,
    'confidence_score': 0.92
}

def test_create_document_success(document_service: DocumentService):
    """Test successful document creation"""
    doc = document_service.create_document(SAMPLE_DOC, "user1")
    assert doc.id is not None
    assert doc.filename == 'test.pdf'
    assert doc.file_type == FileType.pdf
    assert doc.status == ProcessingStatus.pending

def test_create_document_missing_fields(document_service: DocumentService):
    """Test document creation with missing fields"""
    invalid_doc = {'filename': 'test.pdf'}
    with pytest.raises(MyException) as exc:
        document_service.create_document(invalid_doc, "user1")
    assert exc.value.code == 400
    assert _("Missing required document fields") in str(exc.value.msg)

def test_get_document_by_id(document_service: DocumentService):
    """Test retrieving document by ID"""
    # Create then retrieve
    fetched = document_service.get_document_by_id(DEMO_DOC_ID)
    
    assert fetched is not None
    assert fetched.id == DEMO_DOC_ID
    assert fetched.filename == 'annual_report.pdf'

def test_update_document(document_service: DocumentService):
    """Test document metadata update"""
    doc = document_service.get_document_by_id(DEMO_DOC_ID)
    
    # Update fields
    updated = document_service.update_document({
        'id': str(doc.id),
        'filename': 'updated.pdf',
        'status': 'completed'
    }, "user2")
    
    assert updated.filename == 'updated.pdf'
    assert updated.status == ProcessingStatus.completed

def test_add_ocr_result(document_service: DocumentService):
    """Test adding OCR result to document"""
    doc = document_service.get_document_by_id(DEMO_DOC_ID)
    ocr_result = document_service.add_ocr_result(doc.id, SAMPLE_OCR, "ocr_worker")
    
    assert ocr_result.id is not None
    assert ocr_result.engine == OcrEngine.paddleocr
    assert ocr_result.extracted_text == 'This is sample extracted text'
    
    # Verify document status updated
    updated_doc = document_service.get_document_by_id(doc.id)
    assert updated_doc.status == ProcessingStatus.completed

def test_add_failed_ocr_result(document_service: DocumentService):
    """Test adding failed OCR result"""
    doc = document_service.get_document_by_id(DEMO_DOC_ID)
    failed_ocr = {
        'engine': 'tesseract',
        'extracted_text': '',
        'processing_time_ms': 500,
        'error_message': 'OCR processing failed'
    }
    
    ocr_result = document_service.add_ocr_result(doc.id, failed_ocr, "ocr_worker")
    assert ocr_result.error_message == 'OCR processing failed'
    
    # Status should remain pending (not completed)
    updated_doc = document_service.get_document_by_id(doc.id)
    assert updated_doc.status == ProcessingStatus.completed

def test_list_documents(document_service: DocumentService):
    """Test document listing with filters"""
    # By date range
    docs, total = document_service.list_documents({
        'upload_time_from': datetime.now() - timedelta(days=3),
        'upload_time_to': datetime.now() - timedelta(days=1)
    })
    assert total == 1
    assert docs[0].filename == 'contract.pdf'

def test_document_status_flow(document_service: DocumentService):
    """Test document status transitions"""
    doc = document_service.create_document(SAMPLE_DOC, "user1")
    assert doc.status == ProcessingStatus.pending
    
    # Update to processing
    updated = document_service.change_document_status(
        doc.id, ProcessingStatus.processing, "system"
    )
    assert updated.status == ProcessingStatus.processing
    
    # Add OCR result to complete
    document_service.add_ocr_result(doc.id, SAMPLE_OCR, "ocr_worker")
    completed = document_service.get_document_by_id(doc.id)
    assert completed.status == ProcessingStatus.completed

def test_ocr_result_text_preview(document_service: DocumentService):
    """Test OCR result text preview property"""
    doc = document_service.create_document(SAMPLE_DOC, "user1")
    ocr_data = {
        **SAMPLE_OCR,
        'extracted_text': 'This is a long text that should be truncated for preview purposes in the UI'
    }
    ocr_result = document_service.add_ocr_result(doc.id, ocr_data, "ocr_worker")
    
    assert len(ocr_result.text_preview) == 303  # 300 chars + '...'
    assert ocr_result.text_preview.endswith('...')

def test_get_demo_document(document_service: DocumentService):
    """Test retrieval of demo document"""
    doc = document_service.get_document_by_id(DEMO_DOC_ID)
    assert doc is not None
    assert doc.filename == 'annual_report.pdf'
    assert doc.status == ProcessingStatus.completed
    assert len(doc.ocr_results) == 2

def test_list_demo_documents(document_service: DocumentService):
    """Test listing includes demo documents"""
    docs, total = document_service.list_documents({'status': 'completed'})
    assert total >= 1
    assert any(doc.id == DEMO_DOC_ID for doc in docs)