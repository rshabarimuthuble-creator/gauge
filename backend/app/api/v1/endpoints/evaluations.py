from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.schemas.evaluation_run import EvaluationRunRead, EvaluationRunDetailRead, EvaluationRunCreate
from app.schemas.evaluation_result import EvaluationResultRead
from app.services.evaluation_service import EvaluationService, RunEntityNotFoundError, DuplicateEvaluationError
from app.core.logging import logger

router = APIRouter()


@router.get(
    "",
    response_model=List[EvaluationRunRead],
    summary="List all evaluation runs",
    description="Returns benchmark evaluation runs with aggregate metrics (pass rate, latency, case counts).",
)
def get_evaluations(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    db: Session = Depends(get_db),
) -> List[EvaluationRunRead]:
    try:
        runs = EvaluationService.get_all(db, skip=skip, limit=limit)
        return [EvaluationRunRead.model_validate(r) for r in runs]
    except SQLAlchemyError as exc:
        logger.error("Failed to fetch evaluation runs: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable. Please check connectivity.",
        )


@router.post(
    "",
    response_model=EvaluationRunDetailRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start an evaluation run",
    description=(
        "Executes a benchmark evaluation run against a registered dataset and agent version. "
        "Calculates exact-match correctness, records per-case outputs, latency, token estimations, "
        "and updates aggregate run-level metrics."
    ),
)
def create_evaluation(
    run_in: EvaluationRunCreate,
    background: Optional[bool] = Query(None, description="Execute evaluation asynchronously in background"),
    db: Session = Depends(get_db),
) -> EvaluationRunDetailRead:
    try:
        is_bg = background if background is not None else (run_in.background is True)
        run = EvaluationService.create_and_execute(db, run_in, background=is_bg)
        return EvaluationRunDetailRead.model_validate(run)
    except DuplicateEvaluationError as exc:
        logger.warning("Duplicate evaluation launch rejected: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except RunEntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except SQLAlchemyError as exc:
        logger.error("Database error during evaluation creation: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to execute evaluation run due to database error.",
        )



@router.get(
    "/{run_id}",
    response_model=EvaluationRunDetailRead,
    summary="Get evaluation run details",
    description="Returns an evaluation run by its ID, including aggregate metrics and individual case execution results.",
)
def get_evaluation(
    run_id: str,
    db: Session = Depends(get_db),
) -> EvaluationRunDetailRead:
    try:
        run = EvaluationService.get_run_detail(db, run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evaluation run with ID '{run_id}' not found.",
            )
        return EvaluationRunDetailRead.model_validate(run)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("Database error fetching evaluation run %s: %s", run_id, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable.",
        )


@router.get(
    "/{run_id}/results",
    response_model=List[EvaluationResultRead],
    summary="Get case-level results for a run",
    description="Retrieves persisted individual test-case execution results with optional filtering by status (passed, failed, error, unscored).",
)
def get_evaluation_results(
    run_id: str,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by result status: passed, failed, error, unscored"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[EvaluationResultRead]:
    try:
        # Verify run exists
        run = EvaluationService.get_by_id(db, run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evaluation run with ID '{run_id}' not found.",
            )
        results = EvaluationService.get_run_results(
            db,
            run_id=run_id,
            status_filter=status_filter,
            skip=skip,
            limit=limit,
        )
        return [EvaluationResultRead.model_validate(r) for r in results]
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("Database error fetching results for run %s: %s", run_id, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable.",
        )
