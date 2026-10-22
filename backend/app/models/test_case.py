import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.dataset import EvaluationDataset


class EvaluationTestCase(Base):
    """
    Represents an individual benchmark test case belonging to an EvaluationDataset.
    Includes stable case identifier, input prompt, expected output/criteria, and optional metadata.
    """
    __tablename__ = "evaluation_test_cases"

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
    case_identifier: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    input_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    criteria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    scoring_method: Mapped[Optional[str]] = mapped_column(String(64), default="exact_match", nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    dataset: Mapped["EvaluationDataset"] = relationship(
        "EvaluationDataset",
        back_populates="test_cases",
    )

    __table_args__ = (
        Index("ix_evaluation_test_cases_dataset_case", "dataset_id", "case_identifier"),
    )

    def __repr__(self) -> str:
        return f"<EvaluationTestCase(id={self.id}, case_identifier='{self.case_identifier}')>"
