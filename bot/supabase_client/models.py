from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class User(BaseModel):
    id: Optional[int] = None
    telegram_id: int
    username: Optional[str] = None
    language: Optional[str] = 'en'
    isAudio: Optional[bool] = False
    notification: Optional[bool] = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Document(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    category_id: Optional[str] = None
    subdirectory_id: Optional[str] = None
    url: str
    short_description: str
    description: str
    tags: Optional[List[str]] = None
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None