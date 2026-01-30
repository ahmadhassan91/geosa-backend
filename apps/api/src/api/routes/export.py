"""
Export Routes

API endpoints for exporting analysis results.
"""

import json
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse

from src.api.dependencies import CurrentUser, DbSession
from src.application.dtos import ExportResponse
from src.infrastructure.config import settings
from src.infrastructure.repositories import (
    SQLAlchemyAnomalyRepository,
    SQLAlchemyDatasetRepository,
    SQLAlchemyRunRepository,
)

router = APIRouter(prefix="/runs/{run_id}/export", tags=["export"])


@router.get("/json")
async def export_json_report(
    run_id: UUID,
    db: DbSession,
    user: CurrentUser,
    include_reviewed_only: bool = False,
):
    """
    Export run results as JSON report.
    
    Returns a comprehensive JSON report with:
    - Run metadata
    - Dataset info
    - All anomalies with explanations
    - Configuration snapshot
    """
    run_repo = SQLAlchemyRunRepository(db)
    dataset_repo = SQLAlchemyDatasetRepository(db)
    anomaly_repo = SQLAlchemyAnomalyRepository(db)
    
    run = await run_repo.get_by_id(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )
    
    dataset = await dataset_repo.get_by_id(run.dataset_id)
    
    # Get anomalies
    decision_filter = "!pending" if include_reviewed_only else None
    anomalies, _ = await anomaly_repo.get_by_run(
        run_id=run_id,
        page=1,
        page_size=10000,  # Get all
        decision_filter=decision_filter,
    )
    
    summary = await anomaly_repo.get_summary(run_id)
    
    from datetime import datetime
    
    report = {
        "report_type": "hydroq_qc_analysis",
        "generated_at": datetime.utcnow().isoformat(),
        "run": {
            "id": str(run.id),
            "dataset_id": str(run.dataset_id),
            "status": run.status.value,
            "model_version": run.model_version,
            "config_hash": run.config_hash,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "duration_seconds": run.duration_seconds,
        },
        "dataset": {
            "name": dataset.name if dataset else None,
            "file_type": dataset.file_type if dataset else None,
            "crs": dataset.crs if dataset else None,
            "bounds": dataset.bounds if dataset else None,
            "z_range": {
                "min": dataset.z_min,
                "max": dataset.z_max,
                "mean": dataset.z_mean,
            } if dataset else None,
        },
        "summary": {
            "total_anomalies": run.total_anomalies,
            "by_confidence": summary.get("by_confidence", {}),
            "by_type": summary.get("by_type", {}),
            "by_decision": summary.get("by_decision", {}),
        },
        "anomalies": [
            {
                "id": str(a.id),
                "type": a.anomaly_type.value,
                "centroid": [a.centroid_x, a.centroid_y],
                "area_sq_meters": a.area_sq_meters,
                "probability": round(a.anomaly_probability, 4),
                "confidence": a.confidence_level.value,
                "qc_priority": round(a.qc_priority, 4),
                "review_decision": a.review_decision.value,
                "explanation": a.explanation,
                "local_stats": {
                    "depth_mean": a.local_depth_mean,
                    "depth_std": a.local_depth_std,
                    "neighbor_count": a.neighbor_count,
                },
            }
            for a in anomalies
        ],
        "config_snapshot": run.config_snapshot,
    }
    
    return JSONResponse(content=report)


@router.get("/geojson")
async def export_geojson(
    run_id: UUID,
    db: DbSession,
    user: CurrentUser,
    include_reviewed_only: bool = False,
):
    """
    Export anomalies as GeoJSON FeatureCollection.
    
    Can be loaded directly into GIS software or map viewers.
    """
    run_repo = SQLAlchemyRunRepository(db)
    anomaly_repo = SQLAlchemyAnomalyRepository(db)
    
    run = await run_repo.get_by_id(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )
    
    # Get anomalies
    decision_filter = "!pending" if include_reviewed_only else None
    anomalies, _ = await anomaly_repo.get_by_run(
        run_id=run_id,
        page=1,
        page_size=10000,
        decision_filter=decision_filter,
    )
    
    from datetime import datetime
    
    geojson = {
        "type": "FeatureCollection",
        "properties": {
            "run_id": str(run.id),
            "model_version": run.model_version,
            "generated_at": datetime.utcnow().isoformat(),
        },
        "features": [a.to_geojson_feature() for a in anomalies],
    }
    
    return JSONResponse(content=geojson)


@router.get("/heatmap")
async def download_heatmap(
    run_id: UUID,
    db: DbSession,
    user: CurrentUser,
):
    """
    Download the anomaly probability heatmap as GeoTIFF.
    
    Returns a raster where each pixel value is the anomaly probability (0-1).
    """
    run_repo = SQLAlchemyRunRepository(db)
    run = await run_repo.get_by_id(run_id)
    
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )
    
    if run.heatmap_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Heatmap not available for this run",
        )
    
    heatmap_path = Path(run.heatmap_path)
    
    if not heatmap_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Heatmap file not found on disk",
        )
    
    return FileResponse(
        path=heatmap_path,
        filename=f"run_{run_id}_heatmap.tif",
        media_type="image/tiff",
    )


@router.get("/review-report")
async def export_review_report(
    run_id: UUID,
    db: DbSession,
    user: CurrentUser,
):
    """
    Export a review report with all decisions made.
    
    Includes:
    - Summary of review decisions
    - List of all reviewed anomalies with reviewer info
    - Audit trail
    """
    from src.infrastructure.repositories import SQLAlchemyReviewLogRepository
    from datetime import datetime
    
    run_repo = SQLAlchemyRunRepository(db)
    anomaly_repo = SQLAlchemyAnomalyRepository(db)
    review_log_repo = SQLAlchemyReviewLogRepository(db)
    
    run = await run_repo.get_by_id(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )
    
    # Get summary
    summary = await anomaly_repo.get_summary(run_id)
    
    # Get all review logs
    review_logs = await review_log_repo.get_by_run(run_id)
    
    report = {
        "report_type": "hydroq_qc_review_report",
        "generated_at": datetime.utcnow().isoformat(),
        "run_id": str(run_id),
        "model_version": run.model_version,
        "summary": {
            "total_anomalies": run.total_anomalies,
            "review_status": summary.get("by_decision", {}),
            "pending_count": summary.get("by_decision", {}).get("pending", 0),
            "reviewed_count": (
                summary.get("by_decision", {}).get("accepted", 0) +
                summary.get("by_decision", {}).get("rejected", 0)
            ),
        },
        "review_history": [
            {
                "id": str(log.id),
                "anomaly_id": str(log.anomaly_id),
                "decision": log.decision.value,
                "comment": log.comment,
                "reviewer": log.reviewer_username,
                "reviewed_at": log.created_at.isoformat(),
                "anomaly_score_at_review": log.anomaly_score_at_review,
            }
            for log in review_logs
        ],
    }
    
    return JSONResponse(content=report)


@router.get("/s102")
async def export_s102_format(
    run_id: UUID,
    db: DbSession,
    user: CurrentUser,
):
    """
    Export run results in S-102 (IHO Bathymetric Surface) compliant HDF5 format.
    
    S-102 is part of the IHO S-100 Universal Hydrographic Data Model.
    This creates an HDF5 file containing the bathymetry grid and metadata.
    """
    from datetime import datetime
    from src.infrastructure.s102_export import export_s102_h5
    
    run_repo = SQLAlchemyRunRepository(db)
    dataset_repo = SQLAlchemyDatasetRepository(db)
    anomaly_repo = SQLAlchemyAnomalyRepository(db)
    
    run = await run_repo.get_by_id(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )
    
    dataset = await dataset_repo.get_by_id(run.dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found for this run",
        )
    
    # Get all anomalies
    anomalies, _ = await anomaly_repo.get_by_run(
        run_id=run_id,
        page=1,
        page_size=100000,
    )
    
    # Prepare export path
    output_dir = Path(settings.data_dir) / "exports" / f"run_{run_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"run_{run_id}_S102_v2.2.h5"
    
    # Format anomalies for exporter
    anomalies_data = [
        {
            "id": str(a.id),
            "anomaly_type": a.anomaly_type.value,
            "confidence_level": a.confidence_level.value,
            "centroid_x": a.centroid_x,
            "centroid_y": a.centroid_y,
            "anomaly_probability": a.anomaly_probability,
            "review_decision": a.review_decision.value,
        }
        for a in anomalies
    ]
    
    depth_stats = {
        "z_min": dataset.z_min or 0, 
        "z_max": dataset.z_max or 0, 
        "z_mean": dataset.z_mean or 0, 
        "z_std": dataset.z_std or 0
    }
    
    try:
        print(f"DEBUG S102: Starting export for run {run_id}")
        print(f"DEBUG S102: dataset_path={dataset.file_path}")
        print(f"DEBUG S102: output_path={output_path}")
        
        file_path = export_s102_h5(
            dataset_path=str(dataset.file_path),
            dataset_name=dataset.name,
            bounds=dataset.bounds or {},
            resolution=dataset.resolution,
            depth_stats=depth_stats,
            anomalies=anomalies_data,
            output_path=output_path
        )
        
        print(f"DEBUG S102: Export successful to {file_path}")
        
        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type="application/x-hdf5"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"DEBUG S102 ERROR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"S-102 export failed: {str(e)}"
        )
