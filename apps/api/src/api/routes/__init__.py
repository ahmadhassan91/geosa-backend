"""
API Routes Package

Exports all route modules.
"""

from src.api.routes.auth import router as auth_router
from src.api.routes.datasets import router as datasets_router
from src.api.routes.runs import router as runs_router
from src.api.routes.anomalies import router as anomalies_router
from src.api.routes.export import router as export_router
from src.api.routes.quality import router as quality_router
from src.api.routes.production import router as production_router

__all__ = [
    "auth_router",
    "datasets_router",
    "runs_router",
    "anomalies_router",
    "export_router",
    "quality_router",
    "production_router",
]

