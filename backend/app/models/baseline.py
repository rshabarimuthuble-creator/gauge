import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.dataset import EvaluationDataset
    from app.models.evaluation_run import EvaluationRun
    from app.models.agent_version import AgentVersion


class EvaluationBaseline(Base):
    """
    Represents an active or historical baseline benchmark evaluation run for an EvaluationDataset.
    Guarantees persistence across restarts and provides a reference for version regression comparisons.
    """
    __tablename__ = "evaluation_baselines"

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
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    dataset: Mapped["EvaluationDataset"] = relationship("EvaluationDataset")
    run: Mapped["EvaluationRun"] = relationship("EvaluationRun")
    agent_version: Mapped["AgentVersion"] = relationship("AgentVersion")

    __table_args__ = (
        Index("ix_evaluation_baselines_dataset_active", "dataset_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<EvaluationBaseline(id={self.id}, dataset_id='{self.dataset_id}', run_id='{self.run_id}', active={self.is_active})>"
