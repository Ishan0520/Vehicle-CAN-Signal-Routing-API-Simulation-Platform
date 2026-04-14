# models/signal.py
# Defines the shape of a database record.

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SignalRecord(BaseModel):
    id: Optional[int] = None
    feature_name: str
    signal_name: str
    signal_value: float
    can_message_id: int
    raw_bytes: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True