"""
Data Transfer Objects (DTOs)

Pydantic v2 models for API request/response validation.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# =============================================================================
# Base Models
# =============================================================================

class BaseDTO(BaseModel):
    """Base DTO with common configuration."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


# =============================================================================
# User DTOs
# =============================================================================

class UserCreate(BaseDTO):
    """Request to create a new user."""
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(...)
    password: str = Field(..., min_length=8)
    role: str = Field(default="viewer")


class UserResponse(BaseDTO):
    """User response without sensitive data."""
    id: UUID
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseDTO):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseDTO):
    """Login request."""
    username: str
    password: str


# =============================================================================
# Dataset DTOs
# =============================================================================

class DatasetCreate(BaseDTO):
    """Request to create a dataset (metadata only - file uploaded separately)."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)


class DatasetResponse(BaseDTO):
    """Dataset response."""
    id: UUID
    name: str
    description: str
    file_path: str
    file_type: str
    file_size_bytes: int
    crs: str | None = None
    bounds: dict[str, float] | None = None
    width: int | None = None
    height: int | None = None
    resolution: tuple[float, float] | None = None
    point_count: int | None = None
    z_min: float | None = None
    z_max: float | None = None
    z_mean: float | None = None
    z_std: float | None = None
    nodata_percentage: float | None = None
    created_by: UUID | None = None
    created_at: datetime


class DatasetListResponse(BaseDTO):
    """Paginated list of datasets."""
    items: list[DatasetResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Run DTOs
# =============================================================================

class RunCreate(BaseDTO):
    """Request to start a new analysis run."""
    dataset_id: UUID
    # Optional config overrides
    config_overrides: dict[str, Any] | None = None


class RunResponse(BaseDTO):
    """Analysis run response."""
    id: UUID
    dataset_id: UUID
    status: str
    config_hash: str
    model_version: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    total_anomalies: int = 0
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0
    heatmap_path: str | None = None
    geojson_path: str | None = None
    report_path: str | None = None
    error_message: str | None = None
    created_by: UUID | None = None
    created_at: datetime


class RunListResponse(BaseDTO):
    """Paginated list of runs."""
    items: list[RunResponse]
    total: int
    page: int
    page_size: int


class RunStatusResponse(BaseDTO):
    """Run status for polling."""
    id: UUID
    status: str
    progress_percent: int = 0
    current_step: str | None = None
    error_message: str | None = None


# =============================================================================
# Anomaly DTOs
# =============================================================================

class AnomalyExplanation(BaseDTO):
    """Structured explanation of why this was flagged."""
    primary_reason: str
    features: dict[str, float]
    thresholds: dict[str, float]
    detector_flags: list[str]


class AnomalyResponse(BaseDTO):
    """Single anomaly response."""
    id: UUID
    run_id: UUID
    centroid_x: float
    centroid_y: float
    geometry: dict[str, Any]
    area_sq_meters: float | None = None
    anomaly_type: str
    anomaly_probability: float
    confidence_level: str
    qc_priority: float
    explanation: AnomalyExplanation | dict[str, Any]
    local_depth_mean: float | None = None
    local_depth_std: float | None = None
    neighbor_count: int | None = None
    review_decision: str
    created_at: datetime


class AnomalyListResponse(BaseDTO):
    """Paginated list of anomalies."""
    items: list[AnomalyResponse]
    total: int
    page: int
    page_size: int
    # Summary stats
    by_confidence: dict[str, int]
    by_type: dict[str, int]
    by_decision: dict[str, int]


class AnomalySummary(BaseDTO):
    """Anomaly summary for dashboard."""
    total: int
    pending: int
    accepted: int
    rejected: int
    by_confidence: dict[str, int]
    avg_priority: float


# =============================================================================
# Review DTOs
# =============================================================================

class ReviewSubmit(BaseDTO):
    """Request to submit a review decision."""
    decision: str = Field(..., pattern=r"^(accepted|rejected)$")
    comment: str | None = Field(default=None, max_length=2000)
    
    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        if v not in ("accepted", "rejected"):
            raise ValueError("Decision must be 'accepted' or 'rejected'")
        return v


class ReviewResponse(BaseDTO):
    """Review log response."""
    id: UUID
    anomaly_id: UUID
    run_id: UUID
    decision: str
    comment: str | None = None
    reviewer_id: UUID | None = None
    reviewer_username: str | None = None
    model_version: str | None = None
    created_at: datetime


class ReviewListResponse(BaseDTO):
    """List of review history."""
    items: list[ReviewResponse]
    total: int


class BulkReviewSubmit(BaseDTO):
    """Bulk review submission."""
    anomaly_ids: list[UUID]
    decision: str = Field(..., pattern=r"^(accepted|rejected)$")
    comment: str | None = Field(default=None, max_length=2000)


# =============================================================================
# Export DTOs
# =============================================================================

class ExportRequest(BaseDTO):
    """Request to export run results."""
    format: str = Field(default="json", pattern=r"^(json|geojson|pdf)$")
    include_reviewed_only: bool = False
    include_features: bool = False


class ExportResponse(BaseDTO):
    """Export result."""
    download_url: str
    filename: str
    format: str
    file_size_bytes: int
    created_at: datetime


# =============================================================================
# Report DTOs
# =============================================================================

class RunReport(BaseDTO):
    """Full run report for export."""
    run: RunResponse
    dataset: DatasetResponse
    anomaly_summary: AnomalySummary
    anomalies: list[AnomalyResponse]
    config_snapshot: dict[str, Any]
    generated_at: datetime


# =============================================================================
# Health & Metrics
# =============================================================================

class HealthResponse(BaseDTO):
    """Health check response."""
    status: str
    version: str
    database: str
    timestamp: datetime


class MetricsResponse(BaseDTO):
    """System metrics."""
    total_datasets: int
    total_runs: int
    total_anomalies: int
    pending_reviews: int
    recent_runs_7d: int
