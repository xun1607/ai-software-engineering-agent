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
    
    # Environment Validation telemetry columns
    validator_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    validator_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    validator_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    validation_feedback: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


def init_local_db() -> None:
    from shared.db import ENGINE, text
    Base.metadata.create_all(bind=ENGINE)
    
    # Simple migration support for sqlite: add validation columns if they don't exist
    new_columns = [
        ("validator_name", "VARCHAR(255)"),
        ("validator_type", "VARCHAR(100)"),
        ("validator_latency_ms", "INTEGER"),
        ("exit_code", "INTEGER"),
        ("validation_feedback", "VARCHAR(1000)")
    ]
    with ENGINE.begin() as conn:
        for col_name, col_type in new_columns:
            try:
                conn.execute(text(f"ALTER TABLE agent_execution_logs ADD COLUMN {col_name} {col_type}"))
                print(f"🔧 [DB MIGRATION] Added column {col_name} successfully.")
            except Exception:
                # Column probably already exists, which is fine
                pass

# Automatically run local SQLite migrations on import to keep schemas synchronized
try:
    init_local_db()
except Exception as e:
    import logging
    logging.warning(f"Database local auto-migration failed or skipped: {e}")
