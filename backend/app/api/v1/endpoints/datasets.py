from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.schemas.dataset import EvaluationDatasetRead, EvaluationDatasetCreate
from app.schemas.test_case import EvaluationTestCaseRead, EvaluationTestCaseCreate
from app.services.dataset_service import (
    DatasetService,
    DatasetValidationError,
    DatasetDuplicateError,
)
from app.core.logging import logger

router = APIRouter()


class DatasetImportPayload(BaseModel):
    content: str = Field(..., min_length=1, description="Raw JSON or JSONL dataset string")
    name: Optional[str] = Field(default=None, description="Optional override name for dataset")


class CaseImportPayload(BaseModel):
    content: str = Field(..., min_length=1, description="Raw JSON or JSONL test cases string")


@router.get(
    "",
    response_model=List[EvaluationDatasetRead],
    summary="List all evaluation datasets",
    description="Returns all stored benchmark evaluation datasets with test case counts.",
)
def get_datasets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[EvaluationDatasetRead]:
    try:
        datasets = DatasetService.get_all(db, skip=skip, limit=limit)
        return [EvaluationDatasetRead.model_validate(d) for d in datasets]
    except SQLAlchemyError as exc:
        logger.error("Failed to fetch evaluation datasets: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable. Please check connectivity.",
        )


@router.post(
    "",
    response_model=EvaluationDatasetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new evaluation dataset",
    description="Registers a new benchmark dataset in Gauge, optionally populated with initial test cases.",
)
def create_dataset(
    dataset_in: EvaluationDatasetCreate,
    db: Session = Depends(get_db),
) -> EvaluationDatasetRead:
    try:
        dataset = DatasetService.create(db, dataset_in)
        return EvaluationDatasetRead.model_validate(dataset)
    except DatasetDuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except DatasetValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except SQLAlchemyError as exc:
        logger.error("Failed to create evaluation dataset: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to save dataset due to database error.",
        )


@router.post(
    "/import",
    response_model=EvaluationDatasetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Import dataset from JSON or JSONL",
    description="Imports a complete benchmark dataset from raw JSON or JSONL format, validating duplicate IDs.",
)
def import_dataset(
    payload: DatasetImportPayload,
    db: Session = Depends(get_db),
) -> EvaluationDatasetRead:
    try:
        dataset = DatasetService.import_dataset(db, payload.content, default_name=payload.name)
        return EvaluationDatasetRead.model_validate(dataset)
    except DatasetDuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except DatasetValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except SQLAlchemyError as exc:
        logger.error("Failed to import dataset: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error while importing dataset.",
        )


@router.post(
    "/seed_curated",
    response_model=EvaluationDatasetRead,
    status_code=status.HTTP_200_OK,
    summary="Seed curated benchmark dataset",
    description="Seeds the curated 36-case general benchmark suite if it does not already exist.",
)
def seed_curated_dataset(
    db: Session = Depends(get_db),
) -> EvaluationDatasetRead:
    try:
        dataset = DatasetService.seed_curated_benchmark_if_needed(db)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Curated benchmark dataset fixture could not be loaded.",
            )
        return EvaluationDatasetRead.model_validate(dataset)
    except Exception as exc:
        logger.error("Failed to seed curated benchmark: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed curated benchmark: {str(exc)}",
        )


@router.get(
    "/{dataset_id}",
    response_model=EvaluationDatasetRead,
    summary="Get dataset by ID",
    description="Returns dataset details including associated test cases.",
)
def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
) -> EvaluationDatasetRead:
    try:
        dataset = DatasetService.get_by_id(db, dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evaluation dataset with ID '{dataset_id}' not found.",
            )
        return EvaluationDatasetRead.model_validate(dataset)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("Failed to get dataset by ID: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable.",
        )


@router.post(
    "/{dataset_id}/cases",
    response_model=EvaluationTestCaseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a test case to a dataset",
    description="Appends a benchmark test case with input prompt, expected output, and criteria to an existing dataset.",
)
def add_test_case(
    dataset_id: str,
    case_in: EvaluationTestCaseCreate,
    db: Session = Depends(get_db),
) -> EvaluationTestCaseRead:
    try:
        dataset = DatasetService.get_by_id(db, dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evaluation dataset with ID '{dataset_id}' not found.",
            )
        created_case = DatasetService.add_test_case(db, dataset_id, case_in)
        return EvaluationTestCaseRead.model_validate(created_case)
    except DatasetDuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except DatasetValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("Failed to add test case to dataset %s: %s", dataset_id, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to save test case due to database error.",
        )


@router.post(
    "/{dataset_id}/import_cases",
    response_model=List[EvaluationTestCaseRead],
    status_code=status.HTTP_201_CREATED,
    summary="Import test cases into dataset from JSON or JSONL",
    description="Appends multiple test cases from raw JSON or JSONL format, rejecting duplicate IDs.",
)
def import_cases_into_dataset(
    dataset_id: str,
    payload: CaseImportPayload,
    db: Session = Depends(get_db),
) -> List[EvaluationTestCaseRead]:
    try:
        created_cases = DatasetService.import_cases_into_dataset(db, dataset_id, payload.content)
        return [EvaluationTestCaseRead.model_validate(c) for c in created_cases]
    except DatasetDuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except DatasetValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except SQLAlchemyError as exc:
        logger.error("Failed to import cases into dataset %s: %s", dataset_id, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error while importing test cases.",
        )


@router.get(
    "/{dataset_id}/cases",
    response_model=List[EvaluationTestCaseRead],
    summary="List test cases for a dataset",
    description="Retrieves all benchmark test cases belonging to the specified dataset.",
)
def get_dataset_cases(
    dataset_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[EvaluationTestCaseRead]:
    try:
        dataset = DatasetService.get_by_id(db, dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evaluation dataset with ID '{dataset_id}' not found.",
            )
        cases = DatasetService.get_test_cases(db, dataset_id, skip=skip, limit=limit)
        return [EvaluationTestCaseRead.model_validate(c) for c in cases]
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("Failed to get test cases for dataset %s: %s", dataset_id, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable.",
        )
