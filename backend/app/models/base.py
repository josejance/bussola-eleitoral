import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import declared_attr

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class UUIDMixin:
    @declared_attr
    def id(cls):
        return Column(String(36), primary_key=True, default=gen_uuid)


__all__ = ["Base", "TimestampMixin", "UUIDMixin", "gen_uuid"]
