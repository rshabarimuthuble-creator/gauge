import uuid
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, Float, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.dataset import EvaluationDataset
    from app.models.agent_version import AgentVersion
    from app.models.evaluation_result import EvaluationResult


class EvaluationRun(Base):
    """
    Represents an execution instance of a benchmark evaluation run against a dataset
    for a specific agent version. Stores run-level status and aggregate metrics.
    """
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
    )  # pending, running, completed, failed, cancelled
    dataset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("evaluation_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Dataset Snapshot & Configuration
    dataset_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    dataset_snapshot_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scoring_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Aggregate Metrics
    total_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errored_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unscored_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pass_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dataset_coverage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    p95_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Cost and Token Usage Aggregates
    total_cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    dataset: Mapped["EvaluationDataset"] = relationship(
        "EvaluationDataset",
        back_populates="runs",
    )
    agent_version: Mapped["AgentVersion"] = relationship(
        "AgentVersion",
        back_populates="runs",
    )
    results: Mapped[List["EvaluationResult"]] = relationship(
        "EvaluationResult",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="EvaluationResult.created_at",
    )

    __table_args__ = (
        Index("ix_evaluation_runs_dataset_agent", "dataset_id", "agent_version_id"),
    )

    def __repr__(self) -> str:
        return f"<EvaluationRun(id={self.id}, name='{self.name}', status='{self.status}')>"
