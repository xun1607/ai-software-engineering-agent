from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class AgentExecutionLog(Base):
    __tablename__ = "agent_execution_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    task_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    skill_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    baseline_mode: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    quality: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


def init_local_db() -> None:
    from shared.db import ENGINE
    Base.metadata.create_all(bind=ENGINE)
