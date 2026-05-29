from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class QuestionAttempt(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cert_slug: str = Field(index=True)
    question_id: str = Field(index=True)
    selected_option: str
    is_correct: bool = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)


class LabCompletion(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("cert_slug", "lab_id", name="uq_lab_completion"),)

    id: int | None = Field(default=None, primary_key=True)
    cert_slug: str = Field(index=True)
    lab_id: str = Field(index=True)
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
