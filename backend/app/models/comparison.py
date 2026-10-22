import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.dataset import EvaluationDataset
    from app.models.evaluation_run import EvaluationRun


class EvaluationComparison(Base):
    """
    Represents an immutable, persisted benchmark comparison between a baseline EvaluationRun
    and a candidate EvaluationRun. Stores computed metric deltas, regression classifications,
    explanatory reasons, and per-case outcome changes.
    """
    __tablename__ = "evaluation_comparisons"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    dataset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("evaluation_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    baseline_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )  # 'improved', 'regressed', 'unchanged', 'mixed', 'inconclusive'

    is_compatible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    compatibility_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metric Deltas
    pass_rate_delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in percentage points
    accuracy_delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in percentage points
    passed_cases_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_cases_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errored_cases_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unscored_cases_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_latency_ms_delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in milliseconds
    p95_latency_ms_delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost_usd_delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in USD
    tokens_delta: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Per-Case Regression Counts
    newly_failing_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    newly_fixed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    newly_errored_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    newly_unscored_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Denominators & Totals
    total_cases_baseline: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cases_candidate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Detailed Explanations & Snapshots
    reasons_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    thresholds_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    case_comparisons_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    dataset: Mapped["EvaluationDataset"] = relationship("EvaluationDataset")
    baseline_run: Mapped["EvaluationRun"] = relationship(
        "EvaluationRun",
        foreign_keys=[baseline_run_id],
    )
    candidate_run: Mapped["EvaluationRun"] = relationship(
        "EvaluationRun",
        foreign_keys=[candidate_run_id],
    )

    __table_args__ = (
        Index("ix_evaluation_comparisons_baseline_candidate", "baseline_run_id", "candidate_run_id"),
        Index("ix_evaluation_comparisons_dataset_created", "dataset_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<EvaluationComparison(id={self.id}, status='{self.status}', pass_rate_delta={self.pass_rate_delta})>"
