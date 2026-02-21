from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import Base


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class StepStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.QUEUED.value, index=True)

    # What user asked for (free text for now, later structured)
    request_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Final output (JSON string or markdown, later we can store structured JSON)
    result_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    steps: Mapped[list["Step"]] = relationship(
        "Step",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Step(Base):
    __tablename__ = "steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), index=True)

    status: Mapped[str] = mapped_column(String(32), default=StepStatus.PENDING.value, index=True)

    # Tool name like "read_file", "summarize", "make_report"
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)

    # JSON strings (keep simple now)
    input_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["Job"] = relationship("Job", back_populates="steps")