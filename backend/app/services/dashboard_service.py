from typing import Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.dashboard import DashboardSummaryResponse
from app.schemas.evaluation_run import EvaluationRunRead
from app.services.dataset_service import DatasetService
from app.services.version_service import VersionService
from app.services.evaluation_service import EvaluationService
from app.db.session import check_db_connectivity
from app.core.logging import logger


class DashboardService:
    @staticmethod
    def get_summary(db: Session) -> DashboardSummaryResponse:
        """
        Retrieves dashboard overview counts, latest run status, and database connectivity.
        Gracefully handles database errors without raising unhandled 500 exceptions or
        exposing connection secrets.
        """
        is_connected, message = check_db_connectivity()

        if not is_connected:
            return DashboardSummaryResponse(
                datasets_count=0,
                versions_count=0,
                total_runs_count=0,
                latest_run_status=None,
                database_connected=False,
                database_message=message,
                recent_runs=[],
            )

        try:
            datasets_count = DatasetService.count(db)
            versions_count = VersionService.count(db)
            total_runs_count = EvaluationService.count(db)
            latest_run = EvaluationService.get_latest(db)
            recent_runs = EvaluationService.get_all(db, limit=5)

            return DashboardSummaryResponse(
                datasets_count=datasets_count,
                versions_count=versions_count,
                total_runs_count=total_runs_count,
                latest_run_status=latest_run.status if latest_run else None,
                database_connected=True,
                database_message=message,
                recent_runs=[EvaluationRunRead.model_validate(r) for r in recent_runs],
            )
        except SQLAlchemyError as exc:
            logger.error("Database query failed during dashboard summary retrieval: %s", type(exc).__name__)
            return DashboardSummaryResponse(
                datasets_count=0,
                versions_count=0,
                total_runs_count=0,
                latest_run_status=None,
                database_connected=False,
                database_message="Database query execution error",
                recent_runs=[],
            )
