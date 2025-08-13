from datetime import datetime
from typing import Optional, List, Dict, Any, ForwardRef
from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from uuid import UUID
from models.models import ProcessingStatus

# Document Schemas
class Target(BaseModel):
    indicator: str
    value: str
    description: str

class DocumentView(BaseModel):
    id: Optional[str] = Field(None, max_length=50)
    filename: str = Field(..., max_length=255)
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    upload_timestamp: Optional[datetime] = None
    status: Optional[str] = None

class DocumentList(BaseModel):
    search_keywords: Optional[str] = None
    status: Optional[str] = None
    from_time: Optional[datetime] = None
    to_time: Optional[datetime] = None
    sort_by: Optional[str] = None
    desc: Optional[bool] = False
    current: Optional[int] = 1
    page_size: Optional[int] = 20
 