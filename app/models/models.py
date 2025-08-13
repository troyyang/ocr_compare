from enum import Enum
from typing import Optional, Any, Dict
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    String, ForeignKey, Text, Integer, Float, DateTime, Index
)
from sqlalchemy.dialects.postgresql import JSONB, ENUM, UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from sqlalchemy.sql import func
from . import BaseModel

# ---------- Enums ----------
class FileType(str, Enum):
    """Enum for supported file types."""
    pdf = "pdf"
    image = "image"


class OcrEngine(str, Enum):
    """Enum for OCR engines."""
    paddleocr = "paddleocr"
    tesseract = "tesseract"
    easyocr = "easyocr"
    pdfplumber = "pdfplumber"


class ProcessingStatus(str, Enum):
    """Enum for processing status."""
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class UserRole(str, Enum):
    """Enum for user roles."""
    anonymous = "anonymous"
    user = "user"
    admin = "admin"
    moderator = "moderator"

# Create PostgreSQL ENUM types
FileTypeEnum = ENUM(FileType, name="file_type", create_type=True)
OcrEngineEnum = ENUM(OcrEngine, name="ocr_engine", create_type=True)
ProcessingStatusEnum = ENUM(ProcessingStatus, name="processing_status", create_type=True)
UserRoleEnum = ENUM(UserRole, name="user_role", create_type=True)


# ---------- Models ----------
class User(BaseModel):
    """User accounts for the application."""
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(150), unique=True, index=True, comment="Unique username")
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True, comment="User email")
    mobile: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True, comment="Mobile number")
    hashed_password: Mapped[str] = mapped_column(String(255), comment="BCrypt hashed password")
    role: Mapped[UserRole] = mapped_column(UserRoleEnum, default=UserRole.user, comment="User role (user/admin)")

class Document(BaseModel):
    """Uploaded documents for OCR processing."""
    __tablename__ = "documents"

    # File information
    filename: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        comment="Original filename"
    )
    file_type: Mapped[FileType] = mapped_column(
        FileTypeEnum, 
        nullable=False, 
        comment="File type (PDF or Image)"
    )
    file_path: Mapped[str] = mapped_column(
        Text, 
        nullable=False, 
        comment="Storage path to the file"
    )
    file_size: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        comment="File size in bytes"
    )
    
    # Metadata
    upload_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the document was uploaded"
    )
    
    # Processing status
    status: Mapped[ProcessingStatus] = mapped_column(
        ProcessingStatusEnum,
        default=ProcessingStatus.pending,
        nullable=False,
        comment="Current processing status"
    )
    
    # Content for search (populated after OCR)
    searchable_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Combined OCR text for search functionality"
    )

    recommendation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Recommendation for the best OCR engine"
    )
    
    ocr_results = relationship("OcrResult", back_populates="document", cascade="all, delete-orphan")

    # Add index for search
    __table_args__ = (
        Index('idx_document_filename', 'filename'),
        Index('idx_document_upload_time', 'upload_timestamp'),
        Index('idx_document_status', 'status'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "filename": self.filename,
            "file_type": self.file_type.value,
            "file_size": self.file_size,
            "upload_timestamp": self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            "status": self.status.value,
            "recommendation": self.recommendation,
            "ocr_results": [ocr_result.to_dict() for ocr_result in self.ocr_results],
            "searchable_content": self.searchable_content,
            "created_at": self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            "updated_at": self.upload_timestamp.isoformat() if self.upload_timestamp else None,
        }

    def __repr__(self):
        return f"Document(id={self.id}, filename={self.filename}, file_type={self.file_type}, file_size={self.file_size}, upload_timestamp={self.upload_timestamp}, status={self.status})"


class OcrResult(BaseModel):
    """OCR processing results for each engine."""
    __tablename__ = "ocr_results"

    # Foreign key to document
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        ForeignKey("documents.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # OCR engine information
    engine: Mapped[OcrEngine] = mapped_column(
        OcrEngineEnum, 
        nullable=False, 
        comment="OCR engine used"
    )
    
    # OCR results
    extracted_text: Mapped[str] = mapped_column(
        Text, 
        nullable=False, 
        comment="Full extracted text"
    )
    
    # Performance metrics
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Overall confidence score (0-1) if available"
    )
    
    processing_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Processing time in milliseconds"
    )
    
    # Per-page metrics (stored as JSON for flexibility)
    page_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Per-page confidence and other metrics"
    )
    
    # Cost estimation (for cloud engines)
    estimated_cost: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Estimated cost in USD"
    )
    
    # Processing metadata
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When OCR was completed"
    )
    
    # Error information
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if processing failed"
    )
    
    # Relationships
    document = relationship("Document", back_populates="ocr_results")
    
    # Add indexes for performance
    __table_args__ = (
        Index('idx_ocr_document_engine', 'document_id', 'engine'),
        Index('idx_ocr_engine', 'engine'),
        Index('idx_ocr_processed_at', 'processed_at'),
        Index('idx_ocr_confidence', 'confidence_score'),
        Index('idx_ocr_processing_time', 'processing_time_ms'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "engine": self.engine.value,
            "extracted_text": self.extracted_text,
            "text_preview": self.extracted_text[:300] + "..." if len(self.extracted_text) > 300 else self.extracted_text,
            "confidence_score": self.confidence_score,
            "processing_time_ms": self.processing_time_ms,
            "estimated_cost": self.estimated_cost,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "error_message": self.error_message,
        }

    def __repr__(self):
        return f"OcrResult(id={self.id}, document_id={self.document_id}, engine={self.engine}, extracted_text={self.extracted_text}, confidence_score={self.confidence_score}, processing_time_ms={self.processing_time_ms}, estimated_cost={self.estimated_cost}, processed_at={self.processed_at}, error_message={self.error_message})"
    
    @property
    def text_preview(self) -> str:
        """Get first 300 characters of extracted text for UI display."""
        return self.extracted_text[:300] + "..." if len(self.extracted_text) > 300 else self.extracted_text