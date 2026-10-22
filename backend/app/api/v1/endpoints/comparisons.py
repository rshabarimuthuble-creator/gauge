from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.schemas.comparison import (
    EvaluationComparisonCreate,
    EvaluationComparisonRead,
    EvaluationComparisonDetailRead,
)
from app.services.comparison_service import (
    ComparisonService,
    ComparisonValidationError,
    ComparisonNotFoundError,
)
from app.core.logging import logger

router = APIRouter()


@router.post(
    "",
    response_model=EvaluationComparisonDetailRead,
    status_code=status.HTTP_201_CREATED,
    summary="Compare evaluation runs and detect regressions",
    description=(
        "Executes a benchmark comparison between a baseline evaluation run and candidate evaluation run. "
        "Calculates exact metric deltas (pass rate in percentage points, latency in ms, error counts), "
        "identifies newly failing, newly fixed, and newly errored cases, applies configurable regression "
        "thresholds, and classifies overall status ('improved', 'regressed', 'unchanged', 'mixed', 'inconclusive')."
    ),
)
def create_comparison(
    comp_in: EvaluationComparisonCreate,
    db: Session = Depends(get_db),
) -> EvaluationComparisonDetailRead:
    try:
        comparison = ComparisonService.compare_runs(
            db=db,
            candidate_run_id=comp_in.candidate_run_id,
            baseline_run_id=comp_in.baseline_run_id,
            thresholds=comp_in.thresholds,
        )
        return comparison
    except ComparisonValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except SQLAlchemyError as exc:
        logger.error("Database error while creating comparison: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable. Please check connectivity.",
        )


@router.get(
    "",
    response_model=List[EvaluationComparisonRead],
    summary="List saved benchmark comparisons",
    description="Returns saved comparisons with high-level metric deltas and classification statuses.",
)
def get_comparisons(
    dataset_id: Optional[str] = Query(None, description="Filter by benchmark dataset ID"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    db: Session = Depends(get_db),
) -> List[EvaluationComparisonRead]:
    try:
        return ComparisonService.get_all(db=db, dataset_id=dataset_id, skip=skip, limit=limit)
    except SQLAlchemyError as exc:
        logger.error("Database error while fetching comparisons: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable. Please check connectivity.",
        )


@router.get(
    "/{comparison_id}",
    response_model=EvaluationComparisonDetailRead,
    summary="Get comparison details",
    description="Returns complete details of a saved comparison, including all per-case output diffs and latencies.",
)
def get_comparison_detail(
    comparison_id: str,
    db: Session = Depends(get_db),
) -> EvaluationComparisonDetailRead:
    try:
        comp_dict = ComparisonService.get_by_id(db=db, comparison_id=comparison_id, include_details=True)
        if not comp_dict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comparison with ID '{comparison_id}' not found.",
            )
        return EvaluationComparisonDetailRead(**comp_dict)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("Database error while fetching comparison detail: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable. Please check connectivity.",
        )


@router.get(
    "/{comparison_id}/regressions",
    response_model=Dict[str, Any],
    summary="Get regression findings",
    description="Returns high-priority regression alerts, status, explanatory reasons, and newly failing test cases.",
)
def get_comparison_regressions(
    comparison_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    try:
        comp_dict = ComparisonService.get_by_id(db=db, comparison_id=comparison_id, include_details=True)
        if not comp_dict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comparison with ID '{comparison_id}' not found.",
            )

        detail = EvaluationComparisonDetailRead(**comp_dict)
        newly_failing = [c for c in detail.case_comparisons if c.outcome_change == "newly_failing"]
        newly_errored = [c for c in detail.case_comparisons if c.outcome_change == "newly_errored"]
        newly_unscored = [c for c in detail.case_comparisons if c.outcome_change == "newly_unscored"]

        return {
            "comparison_id": detail.id,
            "status": detail.status,
            "is_compatible": detail.is_compatible,
            "reasons": detail.reasons,
            "pass_rate_delta": detail.pass_rate_delta,
            "avg_latency_ms_delta": detail.avg_latency_ms_delta,
            "newly_failing_count": detail.newly_failing_count,
            "newly_errored_count": detail.newly_errored_count,
            "newly_unscored_count": detail.newly_unscored_count,
            "newly_failing_cases": [c.model_dump() for c in newly_failing],
            "newly_errored_cases": [c.model_dump() for c in newly_errored],
            "newly_unscored_cases": [c.model_dump() for c in newly_unscored],
        }
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("Database error while fetching regression findings: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable. Please check connectivity.",
        )
