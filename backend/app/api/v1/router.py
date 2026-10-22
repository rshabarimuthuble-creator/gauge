from fastapi import APIRouter

from app.api.v1.endpoints import dashboard, datasets, versions, evaluations, baselines, comparisons

api_router = APIRouter()

api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["Datasets"])
api_router.include_router(versions.router, prefix="/versions", tags=["Agent Versions"])
api_router.include_router(evaluations.router, prefix="/evaluations", tags=["Evaluations"])
api_router.include_router(baselines.router, prefix="/baselines", tags=["Baselines"])
api_router.include_router(comparisons.router, prefix="/comparisons", tags=["Comparisons"])
