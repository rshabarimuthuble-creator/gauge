import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.evaluation_run import EvaluationRun
    from app.models.test_case import EvaluationTestCase


class EvaluationResult(Base):
    """
    Represents an individual test-case execution result within an EvaluationRun.
    Records actual output, pass/fail/error/unscored status, latency, token usage,
    and detailed diagnostic metadata.
    """
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("evaluation_test_cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    case_identifier: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    input_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actual_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )  # passed, failed, error, unscored
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Numeric score e.g. 1.0, 0.5, 0.0
    scoring_method: Mapped[Optional[str]] = mapped_column(String(64), default="exact_match", nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    token_usage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_estimated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model_provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    run: Mapped["EvaluationRun"] = relationship(
        "EvaluationRun",
        back_populates="results",
    )
    test_case: Mapped[Optional["EvaluationTestCase"]] = relationship(
        "EvaluationTestCase",
    )

    __table_args__ = (
        Index("ix_evaluation_results_run_status", "run_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<EvaluationResult(id={self.id}, case='{self.case_identifier}', status='{self.status}')>"
