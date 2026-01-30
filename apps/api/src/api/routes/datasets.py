"""
Dataset Routes

API endpoints for dataset management.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from src.api.dependencies import CurrentUser, DbSession, HydrographerUser
from src.application.dtos import DatasetResponse, DatasetListResponse
from src.infrastructure.config import settings
from src.infrastructure.repositories import SQLAlchemyDatasetRepository
from src.infrastructure.ml_pipeline import RasterProcessor
from src.infrastructure.config import processing_config
from src.domain.entities import Dataset

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    db: DbSession,
    user: HydrographerUser,
    name: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    description: Annotated[str, Form()] = "",
):
    """
    Upload a new bathymetry dataset.
    
    Supports:
    - GeoTIFF rasters (.tif, .tiff)
    - CSV point clouds (.csv)
    - Parquet point clouds (.parquet)
    """
    # Validate file type
    filename = file.filename or "unknown"
    file_type = _detect_file_type(filename)
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Check file size
    max_size = settings.data_dir  # Will use config
    max_size_bytes = 500 * 1024 * 1024  # 500MB default
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {max_size_bytes / (1024*1024):.0f}MB",
        )
    
    # Save file
    upload_dir = settings.upload_dir
    file_path = upload_dir / f"{user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Extract metadata
    metadata = {}
    if file_type == "geotiff":
        try:
            processor = RasterProcessor(processing_config)
            data, raster_meta = processor.load_raster(str(file_path))
            stats = processor.compute_statistics(data)
            metadata = {**raster_meta, **stats}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to process GeoTIFF: {str(e)}",
            )
    
    # Create dataset entity
    from uuid import uuid4
    dataset = Dataset(
        id=uuid4(),
        name=name,
        description=description,
        file_path=str(file_path),
        file_type=file_type,
        file_size_bytes=file_size,
        crs=metadata.get("crs"),
        bounds=metadata.get("bounds"),
        width=metadata.get("width"),
        height=metadata.get("height"),
        resolution=(metadata.get("resolution")),
        z_min=metadata.get("z_min"),
        z_max=metadata.get("z_max"),
        z_mean=metadata.get("z_mean"),
        z_std=metadata.get("z_std"),
        nodata_percentage=metadata.get("nodata_percentage"),
        created_by=user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    # Persist
    repo = SQLAlchemyDatasetRepository(db)
    created = await repo.create(dataset)
    
    return _to_response(created)


@router.get("", response_model=DatasetListResponse)
async def list_datasets(
    db: DbSession,
    user: CurrentUser,
    page: int = 1,
    page_size: int = 20,
):
    """List all datasets with pagination."""
    repo = SQLAlchemyDatasetRepository(db)
    datasets, total = await repo.list_all(page=page, page_size=page_size)
    
    return DatasetListResponse(
        items=[_to_response(d) for d in datasets],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: UUID,
    db: DbSession,
    user: CurrentUser,
):
    """Get a specific dataset by ID."""
    repo = SQLAlchemyDatasetRepository(db)
    dataset = await repo.get_by_id(dataset_id)
    
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset not found: {dataset_id}",
        )
    
    return _to_response(dataset)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: UUID,
    db: DbSession,
    user: HydrographerUser,
):
    """Delete a dataset."""
    repo = SQLAlchemyDatasetRepository(db)
    deleted = await repo.delete(dataset_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset not found: {dataset_id}",
        )


def _detect_file_type(filename: str) -> str:
    """Detect file type from extension."""
    lower = filename.lower()
    if lower.endswith((".tif", ".tiff", ".geotiff")):
        return "geotiff"
    elif lower.endswith(".csv"):
        return "csv"
    elif lower.endswith(".parquet"):
        return "parquet"
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {filename}. Supported: .tif, .tiff, .csv, .parquet",
        )


def _to_response(dataset: Dataset) -> DatasetResponse:
    """Convert domain entity to response DTO."""
    return DatasetResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        file_path=dataset.file_path,
        file_type=dataset.file_type,
        file_size_bytes=dataset.file_size_bytes,
        crs=dataset.crs,
        bounds=dataset.bounds,
        width=dataset.width,
        height=dataset.height,
        resolution=dataset.resolution,
        point_count=dataset.point_count,
        z_min=dataset.z_min,
        z_max=dataset.z_max,
        z_mean=dataset.z_mean,
        z_std=dataset.z_std,
        nodata_percentage=dataset.nodata_percentage,
        created_by=dataset.created_by,
        created_at=dataset.created_at,
    )
