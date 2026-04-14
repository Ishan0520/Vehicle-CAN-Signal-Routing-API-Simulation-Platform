# models/feature.py
# Defines the shape of data going INTO and OUT OF the API.

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class FeatureRequest(BaseModel):
    feature_name: str = Field(..., examples=["unlock_door"])
    value: float = Field(..., examples=[1, 0, 22.5])


class FeatureResponse(BaseModel):
    success: bool
    feature_name: str
    value: float
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    can_message_id: Optional[int] = None
    can_signal: Optional[str] = None


class MappingEntry(BaseModel):
    feature_name: str
    description: str
    message_name: str
    signal_name: str
    value_map: dict[str, Any]
    default_value: float
    value_description: str