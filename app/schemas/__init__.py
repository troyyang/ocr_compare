from pydantic import BaseModel, Field
from datetime import datetime

class BaseViewModel(BaseModel):
    __abstract__ = True
    id: int = Field(default=None)
    create_time: datetime = Field(default=None)
    update_time: datetime = Field(default=None)
