from datetime import datetime
from typing import Dict, Any
from uuid import UUID

from sqlalchemy import BigInteger, Column, DateTime, String, Integer, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.inspection import inspect
from core.database import DBBase
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func

class BaseModel(DBBase):
    __abstract__ = True
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(150), comment="Created by")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by: Mapped[str] = mapped_column(String(150), comment="Updated by")

    def __repr__(self):
        return f"id={self.id}, created_at={self.created_at}, \
                created_by={self.created_by}, \
                updated_at={self.updated_at}, \
                updated_by={self.updated_by}"

    @classmethod
    def _to_dict_list(self, items, item_class, filter=None):
        if items and isinstance(items, list):
            return [item.to_dict(filter) if isinstance(item, item_class) else item for item in items]
        return []

    def to_dict(self, filter=None) -> Dict[str, Any]:
        # get all column names
        columns = inspect(self).mapper.column_attrs.keys()
        if filter:
            columns = [c for c in columns if c in filter]

        result = {}
        for column in columns:
            value = getattr(self, column)
            # Check if the value is an instance of DateTime and format it accordingly.
            if isinstance(value, datetime):
                # Convert datetime object to ISO 8601 string.
                format = "%Y-%m-%d %H:%M:%S"
                result[column] = value.strftime(format)
            elif isinstance(value, UUID):
                result[column] = str(value)
            else:
                result[column] = value
        
        return result


    