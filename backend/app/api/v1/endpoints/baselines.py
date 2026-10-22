from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.schemas.baseline import EvaluationBaselineCreate, EvaluationBaselineRead
from app.services.baseline_service import (
    BaselineService,
    BaselineValidationError,
    BaselineNotFoundError,
)
from app.core.logging import logger

router = APIRouter()


@router.put(
    "",
    response_model=EvaluationBaselineRead,
    summary="Set or update active baseline for a dataset",
    description=(
        "Designates a completed evaluation run as the active baseline for a dataset. "
        "Any previous active baseline for the dataset is archived to preserve history. "
        "Rejects incomplete, failed, or empty evaluation runs."
    ),
)
def set_baseline(
    baseline_in: EvaluationBaselineCreate,
    db: Session = Depends(get_db),
) -> EvaluationBaselineRead:
    try:
        baseline = BaselineService.set_baseline(
            db=db,
            dataset_id=baseline_in.dataset_id,
            run_id=baseline_in.run_id,
            notes=baseline_in.notes,
        )
        return EvaluationBaselineRead.model_validate(baseline)
    except BaselineValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except SQLAlchemyError as exc:
        logger.error("Database error while designating baseline: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable. Please check connectivity.",
        )


@router.get(
    "",
    response_model=List[EvaluationBaselineRead],
    summary="List all active baselines",
    description="Returns all currently active baselines across all benchmark datasets.",
)
def get_all_active_baselines(
    db: Session = Depends(get_db),
) -> List[EvaluationBaselineRead]:
    try:
        baselines = BaselineService.get_all_active_baselines(db)
        return [EvaluationBaselineRead.model_validate(b) for b in baselines]
    except SQLAlchemyError as exc:
        logger.error("Database error while fetching baselines: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable. Please check connectivity.",
        )


@router.get(
    "/{dataset_id}",
    response_model=EvaluationBaselineRead,
    summary="Get active baseline for a dataset",
    description="Retrieves the currently active baseline for the specified dataset ID.",
)
def get_dataset_baseline(
    dataset_id: str,
    db: Session = Depends(get_db),
) -> EvaluationBaselineRead:
    try:
        baseline = BaselineService.get_active_baseline(db, dataset_id=dataset_id)
        if not baseline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active baseline found for dataset '{dataset_id}'.",
            )
        return EvaluationBaselineRead.model_validate(baseline)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("Database error while fetching dataset baseline: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable. Please check connectivity.",
        )


@router.get(
    "/{dataset_id}/history",
    response_model=List[EvaluationBaselineRead],
    summary="Get baseline history for a dataset",
    description="Returns full audit history of all designated baselines for the dataset.",
)
def get_dataset_baseline_history(
    dataset_id: str,
    db: Session = Depends(get_db),
) -> List[EvaluationBaselineRead]:
    try:
        baselines = BaselineService.get_history(db, dataset_id=dataset_id)
        return [EvaluationBaselineRead.model_validate(b) for b in baselines]
    except SQLAlchemyError as exc:
        logger.error("Database error while fetching baseline history: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable. Please check connectivity.",
        )
