from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get dashboard overview statistics",
    description="Returns aggregate counts for datasets, agent versions, evaluation runs, and current database connectivity status.",
)
def get_dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummaryResponse:
    return DashboardService.get_summary(db)
