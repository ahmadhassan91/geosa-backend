"""
Production Routes

API endpoints for upstream hydrographic production tasks:
- Sounding Selection
- Contour Generation
"""

from datetime import datetime
from uuid import UUID
from typing import Literal

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.api.dependencies import CurrentUser, DbSession
from src.infrastructure.repositories import SQLAlchemyDatasetRepository
from src.domain.services import select_soundings_for_scale, generate_chart_contours

import rasterio
import numpy as np
import traceback
import sys


router = APIRouter(prefix="/production", tags=["production"])


class SoundingSelectionRequest(BaseModel):
    """Request body for sounding selection."""
    dataset_id: UUID
    target_scale: int = 50000
    selection_mode: Literal["shoal", "deep", "representative"] = "shoal"


class ContourGenerationRequest(BaseModel):
    """Request body for contour generation."""
    dataset_id: UUID
    contour_interval: float = 5.0
    smoothing_iterations: int = 3


@router.post("/sounding-selection")
async def generate_soundings(
    request: SoundingSelectionRequest,
    db: DbSession,
    user: CurrentUser,
):
    """
    Generate AI-selected soundings for chart compilation.
    
    Returns shoal-biased soundings appropriate for the target chart scale.
    """
    dataset_repo = SQLAlchemyDatasetRepository(db)
    dataset = await dataset_repo.get_by_id(request.dataset_id)
    
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset not found: {request.dataset_id}",
        )
    
    # Load raster
    try:
        with rasterio.open(dataset.file_path) as src:
            data = src.read(1)
            transform = src.transform
            nodata = src.nodata
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read dataset: {e}",
        )
    
    # Generate soundings
    from src.domain.services.sounding_selection import SoundingSelector
    
    # Scale to cell size mapping
    scale_to_cell = {
        10000: 50,
        25000: 100,
        50000: 200,
        100000: 400,
    }
    closest_scale = min(scale_to_cell.keys(), key=lambda k: abs(k - request.target_scale))
    cell_size = scale_to_cell[closest_scale]
    
    selector = SoundingSelector(
        cell_size_meters=cell_size,
        selection_mode=request.selection_mode,
    )
    try:
        soundings = selector.select_from_grid(data, tuple(transform), nodata)
        result = selector.to_geojson(soundings)
        
        result["properties"]["dataset_id"] = str(request.dataset_id)
        result["properties"]["dataset_name"] = dataset.name
        result["properties"]["target_scale"] = request.target_scale
        result["properties"]["generated_at"] = datetime.utcnow().isoformat() + "Z"
        
        return JSONResponse(content=result)
    except Exception as e:
        traceback.print_exc()
        sys.stdout.flush()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sounding selection failed: {str(e)}",
        )


@router.post("/contours")
async def generate_contours(
    request: ContourGenerationRequest,
    db: DbSession,
    user: CurrentUser,
):
    """
    Generate smoothed depth contours from a dataset.
    
    Uses Chaikin corner-cutting for chart-quality output.
    """
    dataset_repo = SQLAlchemyDatasetRepository(db)
    dataset = await dataset_repo.get_by_id(request.dataset_id)
    
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset not found: {request.dataset_id}",
        )
    
    # Load raster
    try:
        with rasterio.open(dataset.file_path) as src:
            data = src.read(1)
            transform = src.transform
            nodata = src.nodata
            
            # Mask nodata
            if nodata is not None:
                data = np.where(data == nodata, np.nan, data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read dataset: {e}",
        )
    
    # Generate contours
    from src.domain.services.contour_generation import ContourGenerator
    
    generator = ContourGenerator(
        contour_interval=request.contour_interval,
        smoothing_iterations=request.smoothing_iterations,
    )
    try:
        contours = generator.generate(data, tuple(transform))
        result = generator.to_geojson(contours)
        
        result["properties"]["dataset_id"] = str(request.dataset_id)
        result["properties"]["dataset_name"] = dataset.name
        result["properties"]["generated_at"] = datetime.utcnow().isoformat() + "Z"
        
        return JSONResponse(content=result)
    except Exception as e:
        traceback.print_exc()
        sys.stdout.flush()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Contour generation failed: {str(e)}",
        )


@router.get("/capabilities")
async def get_production_capabilities(user: CurrentUser):
    """
    List available production processing capabilities.
    """
    return JSONResponse(content={
        "capabilities": [
            {
                "name": "Sounding Selection",
                "endpoint": "/production/sounding-selection",
                "method": "POST",
                "description": "AI-powered shoal-biased sounding selection for chart compilation",
                "parameters": {
                    "target_scale": "Chart scale (10000, 25000, 50000, 100000)",
                    "selection_mode": "shoal (default), deep, or representative",
                },
            },
            {
                "name": "Contour Generation",
                "endpoint": "/production/contours",
                "method": "POST",
                "description": "Smoothed depth contour generation with Chaikin algorithm",
                "parameters": {
                    "contour_interval": "Depth interval in meters (default: 5)",
                    "smoothing_iterations": "Number of smoothing passes (default: 3)",
                },
            },
        ],
        "planned": [
            "Noise Cleaning (configurable filters)",
            "Seam Detection",
            "Multi-survey Comparison",
        ],
    })
