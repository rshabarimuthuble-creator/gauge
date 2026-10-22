import uuid
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.evaluation_run import EvaluationRun
    from app.models.test_case import EvaluationTestCase


class EvaluationDataset(Base):
    """
    Represents a curated benchmark dataset containing test cases for AI agent evaluation.
    """
    __tablename__ = "evaluation_datasets"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(32), default="v1.0.0", nullable=False)
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
    runs: Mapped[List["EvaluationRun"]] = relationship(
        "EvaluationRun",
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
    test_cases: Mapped[List["EvaluationTestCase"]] = relationship(
        "EvaluationTestCase",
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="EvaluationTestCase.created_at",
    )

    def __repr__(self) -> str:
        return f"<EvaluationDataset(id={self.id}, name='{self.name}')>"
