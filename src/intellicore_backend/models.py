from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Device(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    device_instance: Optional[int] = Field(default=None, index=True)
    address: str = Field(index=True)
    name: str = "Unknown"
    vendor: Optional[str] = None
    model_name: Optional[str] = None
    protocol: str = "bacnet"
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class Point(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    device_id: int = Field(index=True, foreign_key="device.id")
    object_identifier: str = Field(index=True)
    object_name: str = "Unknown"
    object_type: str = "unknown"
    units: Optional[str] = None
    present_value: Optional[str] = None
    last_sampled: datetime = Field(default_factory=datetime.utcnow)
