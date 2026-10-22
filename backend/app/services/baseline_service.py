from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.baseline import EvaluationBaseline
from app.models.evaluation_run import EvaluationRun
from app.models.dataset import EvaluationDataset
from app.models.agent_version import AgentVersion
from app.core.logging import logger


from app.schemas.baseline import EvaluationBaselineRead


class BaselineValidationError(Exception):
    """Raised when a baseline selection fails business validation rules."""
    pass


class BaselineNotFoundError(Exception):
    """Raised when a requested baseline does not exist."""
    pass


class BaselineService:
    @staticmethod
    def _to_read_dto(db: Session, baseline: EvaluationBaseline) -> EvaluationBaselineRead:
        """Converts an EvaluationBaseline ORM model to a typed EvaluationBaselineRead DTO."""
        run = db.get(EvaluationRun, baseline.run_id)
        agent_ver = db.get(AgentVersion, run.agent_version_id) if run else None

        return EvaluationBaselineRead(
            id=baseline.id,
            dataset_id=baseline.dataset_id,
            run_id=baseline.run_id,
            agent_version_id=baseline.agent_version_id,
            is_active=baseline.is_active,
            notes=baseline.notes,
            created_at=baseline.created_at,
            updated_at=baseline.updated_at,
            run_name=run.name if run else None,
            agent_name=agent_ver.name if agent_ver else None,
            agent_version=agent_ver.version if agent_ver else None,
            pass_rate=run.pass_rate if run else None,
        )

    @staticmethod
    def set_baseline(
        db: Session,
        dataset_id: str,
        run_id: str,
        notes: Optional[str] = None,
    ) -> EvaluationBaseline:
        """
        Designates a completed evaluation run as the active baseline for a dataset.
        Enforces that the run is completed, non-empty, and belongs to the specified dataset.
        Deactivates any previous active baseline for the dataset to preserve historical tracking.
        """
        dataset = db.get(EvaluationDataset, dataset_id)
        if not dataset:
            raise BaselineValidationError(f"Dataset with ID '{dataset_id}' not found.")

        run = db.get(EvaluationRun, run_id)
        if not run:
            raise BaselineValidationError(f"Evaluation run with ID '{run_id}' not found.")

        if run.dataset_id != dataset_id:
            raise BaselineValidationError(
                f"Evaluation run '{run_id}' belongs to dataset '{run.dataset_id}', not '{dataset_id}'."
            )

        if run.status != "completed":
            raise BaselineValidationError(
                f"Evaluation run '{run_id}' cannot be set as baseline: status is '{run.status}', expected 'completed'."
            )

        if run.total_cases <= 0:
            raise BaselineValidationError(
                f"Evaluation run '{run_id}' cannot be set as baseline because it executed 0 test cases."
            )

        # Deactivate existing active baseline(s) for this dataset
        stmt = (
            select(EvaluationBaseline)
            .where(
                EvaluationBaseline.dataset_id == dataset_id,
                EvaluationBaseline.is_active == True,  # noqa: E712
            )
        )
        existing_active = db.scalars(stmt).all()
        now = datetime.now(timezone.utc)
        for prev in existing_active:
            prev.is_active = False
            prev.updated_at = now

        # Create new active baseline
        new_baseline = EvaluationBaseline(
            dataset_id=dataset_id,
            run_id=run.id,
            agent_version_id=run.agent_version_id,
            is_active=True,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        db.add(new_baseline)
        db.commit()
        db.refresh(new_baseline)

        logger.info(
            f"Set baseline '{new_baseline.id}' for dataset '{dataset_id}' using run '{run_id}' (agent version '{run.agent_version_id}')"
        )
        return BaselineService._to_read_dto(db, new_baseline)

    @staticmethod
    def get_active_baseline(db: Session, dataset_id: str) -> Optional[EvaluationBaselineRead]:
        """Fetch the currently active baseline for a dataset, if one exists."""
        stmt = (
            select(EvaluationBaseline)
            .where(
                EvaluationBaseline.dataset_id == dataset_id,
                EvaluationBaseline.is_active == True,  # noqa: E712
            )
            .order_by(EvaluationBaseline.created_at.desc())
        )
        baseline = db.scalars(stmt).first()
        if baseline:
            return BaselineService._to_read_dto(db, baseline)
        return None

    @staticmethod
    def get_all_active_baselines(db: Session) -> List[EvaluationBaselineRead]:
        """Fetch all active baselines across all datasets."""
        stmt = (
            select(EvaluationBaseline)
            .where(EvaluationBaseline.is_active == True)  # noqa: E712
            .order_by(EvaluationBaseline.created_at.desc())
        )
        baselines = list(db.scalars(stmt).all())
        return [BaselineService._to_read_dto(db, b) for b in baselines]

    @staticmethod
    def get_history(db: Session, dataset_id: str) -> List[EvaluationBaselineRead]:
        """Fetch all historical baselines for a dataset."""
        stmt = (
            select(EvaluationBaseline)
            .where(EvaluationBaseline.dataset_id == dataset_id)
            .order_by(EvaluationBaseline.created_at.desc())
        )
        baselines = list(db.scalars(stmt).all())
        return [BaselineService._to_read_dto(db, b) for b in baselines]
