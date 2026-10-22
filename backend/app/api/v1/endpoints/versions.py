from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.schemas.agent_version import AgentVersionRead, AgentVersionCreate
from app.services.version_service import VersionService
from app.core.logging import logger

router = APIRouter()


@router.get(
    "",
    response_model=List[AgentVersionRead],
    summary="List all agent and prompt versions",
    description="Returns all registered agent snapshots, models, and prompts. Returns an empty list initially.",
)
def get_versions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> List[AgentVersionRead]:
    try:
        versions = VersionService.get_all(db, skip=skip, limit=limit)
        return [AgentVersionRead.model_validate(v) for v in versions]
    except SQLAlchemyError as exc:
        logger.error("Failed to fetch agent versions: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable. Please check connectivity.",
        )


@router.post(
    "",
    response_model=AgentVersionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new agent version",
    description="Registers an agent version snapshot with model parameters and prompt configuration.",
)
def create_version(
    version_in: AgentVersionCreate,
    db: Session = Depends(get_db),
) -> AgentVersionRead:
    try:
        version = VersionService.create(db, version_in)
        return AgentVersionRead.model_validate(version)
    except SQLAlchemyError as exc:
        logger.error("Failed to create agent version: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to save agent version due to database error.",
        )


@router.get(
    "/{version_id}",
    response_model=AgentVersionRead,
    summary="Get agent version by ID",
)
def get_version(
    version_id: str,
    db: Session = Depends(get_db),
) -> AgentVersionRead:
    try:
        version = VersionService.get_by_id(db, version_id)
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent version with ID '{version_id}' not found.",
            )
        return AgentVersionRead.model_validate(version)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("Failed to get agent version by ID: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service currently unavailable.",
        )
