"""
Run Routes

API endpoints for analysis runs.
"""

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from src.api.dependencies import CurrentUser, DbSession, HydrographerUser
from src.application.dtos import (
    RunCreate,
    RunResponse,
    RunListResponse,
    RunStatusResponse,
)
from src.domain.entities import ConfidenceLevel, ModelRun, RunStatus
from src.infrastructure.config import processing_config, settings
from src.infrastructure.repositories import (
    SQLAlchemyAnomalyRepository,
    SQLAlchemyDatasetRepository,
    SQLAlchemyRunRepository,
)
from src.infrastructure.ml_pipeline import MLPipeline

router = APIRouter(prefix="/runs", tags=["runs"])

# In-memory progress tracking (for PoC - use Redis in production)
_run_progress: dict[str, dict[str, Any]] = {}


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    request: RunCreate,
    background_tasks: BackgroundTasks,
    db: DbSession,
    user: HydrographerUser,
):
    """
    Start a new analysis run on a dataset.
    
    The analysis runs asynchronously. Use GET /runs/{id} to poll for status.
    """
    # Verify dataset exists
    dataset_repo = SQLAlchemyDatasetRepository(db)
    dataset = await dataset_repo.get_by_id(request.dataset_id)
    
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset not found: {request.dataset_id}",
        )
    
    # Create config hash
    import hashlib
    import json
    
    config = processing_config.as_dict
    if request.config_overrides:
        config = _merge_config(config, request.config_overrides)
    
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True).encode()
    ).hexdigest()[:16]
    
    # Create run entity
    run = ModelRun(
        id=uuid4(),
        dataset_id=request.dataset_id,
        status=RunStatus.PENDING,
        config_hash=config_hash,
        config_snapshot=config,
        model_version=MLPipeline.VERSION,
        created_by=user.id,
        created_at=datetime.utcnow(),
    )
    
    # Persist
    run_repo = SQLAlchemyRunRepository(db)
    created_run = await run_repo.create(run)
    
    # Initialize progress tracking
    _run_progress[str(created_run.id)] = {
        "percent": 0,
        "step": "Queued",
    }
    
    # Start background processing
    # Start background processing (direct asyncio task for PoC reliability)
    asyncio.create_task(
        _run_analysis_task(
            run_id=created_run.id,
            dataset_id=dataset.id,
            config=config,
        )
    )
    
    return _to_response(created_run)


@router.get("", response_model=RunListResponse)
async def list_runs(
    db: DbSession,
    user: CurrentUser,
    dataset_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """List analysis runs, optionally filtered by dataset."""
    run_repo = SQLAlchemyRunRepository(db)
    
    if dataset_id:
        runs, total = await run_repo.list_by_dataset(
            dataset_id=dataset_id,
            page=page,
            page_size=page_size,
        )
    else:
        runs, total = await run_repo.list_all(page=page, page_size=page_size)
    
    return RunListResponse(
        items=[_to_response(r) for r in runs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: UUID,
    db: DbSession,
    user: CurrentUser,
):
    """Get a specific run by ID."""
    run_repo = SQLAlchemyRunRepository(db)
    run = await run_repo.get_by_id(run_id)
    
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )
    
    return _to_response(run)


@router.get("/{run_id}/status", response_model=RunStatusResponse)
async def get_run_status(
    run_id: UUID,
    db: DbSession,
    user: CurrentUser,
):
    """Get run status and progress for polling."""
    run_repo = SQLAlchemyRunRepository(db)
    run = await run_repo.get_by_id(run_id)
    
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )
    
    # Get progress from in-memory store
    progress = _run_progress.get(str(run_id), {"percent": 0, "step": None})
    
    return RunStatusResponse(
        id=run.id,
        status=run.status.value,
        progress_percent=progress.get("percent", 0),
        current_step=progress.get("step"),
        error_message=run.error_message,
    )


async def _run_analysis_task(
    run_id: UUID,
    dataset_id: UUID,
    config: dict[str, Any],
):
    """Background task to run the ML analysis pipeline."""
    from src.infrastructure.database import get_session_context
    from src.infrastructure.config import ProcessingConfig
    
    def progress_callback(percent: int, step: str):
        _run_progress[str(run_id)] = {"percent": percent, "step": step}
    
    async with get_session_context() as db:
        run_repo = SQLAlchemyRunRepository(db)
        anomaly_repo = SQLAlchemyAnomalyRepository(db)
        dataset_repo = SQLAlchemyDatasetRepository(db)
        
        # Update status to processing
        run = await run_repo.get_by_id(run_id)
        if run is None:
            return
        
        dataset = await dataset_repo.get_by_id(dataset_id)
        if dataset is None:
            return

        run.status = RunStatus.PROCESSING
        run.started_at = datetime.utcnow()
        await run_repo.update(run)
        
        try:
            # Run pipeline
            from src.infrastructure.ml_pipeline import MLPipeline
            
            proc_config = ProcessingConfig()
            pipeline = MLPipeline(proc_config, settings.output_dir)
            
            anomalies, output_paths = await pipeline.run_analysis(
                dataset=dataset,
                run_id=run_id,
                progress_callback=progress_callback,
            )
            
            # Count by confidence
            high_count = sum(1 for a in anomalies if a.confidence_level == ConfidenceLevel.HIGH)
            medium_count = sum(1 for a in anomalies if a.confidence_level == ConfidenceLevel.MEDIUM)
            low_count = sum(1 for a in anomalies if a.confidence_level == ConfidenceLevel.LOW)
            
            # Save anomalies
            if anomalies:
                await anomaly_repo.create_batch(anomalies)
            
            # Update run with results
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            run.total_anomalies = len(anomalies)
            run.high_confidence_count = high_count
            run.medium_confidence_count = medium_count
            run.low_confidence_count = low_count
            run.heatmap_path = output_paths.get("heatmap")
            run.geojson_path = output_paths.get("geojson")
            
            await run_repo.update(run)
            
            # Update progress
            _run_progress[str(run_id)] = {"percent": 100, "step": "Complete"}
            
        except Exception as e:
            # Update run with error
            run.status = RunStatus.FAILED
            run.completed_at = datetime.utcnow()
            run.error_message = str(e)
            await run_repo.update(run)
            
            _run_progress[str(run_id)] = {"percent": 0, "step": f"Error: {str(e)}"}


def _merge_config(base: dict, overrides: dict) -> dict:
    """Deep merge config overrides."""
    result = base.copy()
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_config(result[key], value)
        else:
            result[key] = value
    return result


def _to_response(run: ModelRun) -> RunResponse:
    """Convert domain entity to response DTO."""
    return RunResponse(
        id=run.id,
        dataset_id=run.dataset_id,
        status=run.status.value,
        config_hash=run.config_hash,
        model_version=run.model_version,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_seconds=run.duration_seconds,
        total_anomalies=run.total_anomalies,
        high_confidence_count=run.high_confidence_count,
        medium_confidence_count=run.medium_confidence_count,
        low_confidence_count=run.low_confidence_count,
        heatmap_path=run.heatmap_path,
        geojson_path=run.geojson_path,
        report_path=run.report_path,
        error_message=run.error_message,
        created_by=run.created_by,
        created_at=run.created_at,
    )
