"""
Domain Entities

Core business entities for the HydroQ-QC-Assistant system.
These are pure Python classes with no external dependencies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    HYDROGRAPHER = "hydrographer"
    VIEWER = "viewer"


class RunStatus(str, Enum):
    """Status of an analysis run."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConfidenceLevel(str, Enum):
    """Confidence level for anomaly detection."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReviewDecision(str, Enum):
    """Review decision for an anomaly."""
    PENDING = "pending"
    ACCEPTED = "accepted"  # Confirmed as real anomaly
    REJECTED = "rejected"  # False positive


class AnomalyType(str, Enum):
    """Types of detected anomalies."""
    SPIKE = "spike"
    HOLE = "hole"
    SEAM = "seam"
    NOISE_BAND = "noise_band"
    DISCONTINUITY = "discontinuity"
    DENSITY_GAP = "density_gap"
    UNKNOWN = "unknown"


@dataclass
class User:
    """User entity."""
    id: UUID
    username: str
    email: str
    hashed_password: str
    role: UserRole
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def can_review(self) -> bool:
        """Check if user can review anomalies."""
        return self.role in (UserRole.ADMIN, UserRole.HYDROGRAPHER)

    def can_manage(self) -> bool:
        """Check if user can manage users and datasets."""
        return self.role == UserRole.ADMIN


@dataclass
class Dataset:
    """
    Dataset entity representing an uploaded bathymetry file.
    
    Supports both raster (GeoTIFF) and point (CSV/Parquet) formats.
    """
    id: UUID
    name: str
    description: str
    file_path: str
    file_type: str  # "geotiff", "csv", "parquet"
    file_size_bytes: int
    
    # Spatial metadata
    crs: str | None = None
    bounds: dict[str, float] | None = None  # {minx, miny, maxx, maxy}
    
    # Raster-specific
    width: int | None = None
    height: int | None = None
    resolution: tuple[float, float] | None = None
    
    # Point-specific
    point_count: int | None = None
    
    # Statistics
    z_min: float | None = None
    z_max: float | None = None
    z_mean: float | None = None
    z_std: float | None = None
    nodata_percentage: float | None = None
    
    # Metadata
    created_by: UUID | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_raster(self) -> bool:
        """Check if dataset is a raster format."""
        return self.file_type == "geotiff"
    
    @property
    def is_point_cloud(self) -> bool:
        """Check if dataset is a point cloud format."""
        return self.file_type in ("csv", "parquet")


@dataclass
class ModelRun:
    """
    Analysis run entity.
    
    Represents a single execution of the anomaly detection pipeline
    on a specific dataset with a specific configuration.
    """
    id: UUID
    dataset_id: UUID
    status: RunStatus
    
    # Configuration snapshot (reproducibility)
    config_hash: str  # Hash of config used
    config_snapshot: dict[str, Any]  # Full config at time of run
    model_version: str  # Version of ML models used
    
    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    # Results summary
    total_anomalies: int = 0
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0
    
    # Output paths
    heatmap_path: str | None = None
    geojson_path: str | None = None
    report_path: str | None = None
    
    # Error handling
    error_message: str | None = None
    
    # Metadata
    created_by: UUID | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def duration_seconds(self) -> float | None:
        """Calculate run duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class Anomaly:
    """
    Detected anomaly entity.
    
    Represents a single detected anomaly with full explainability.
    """
    id: UUID
    run_id: UUID
    
    # Spatial location
    centroid_x: float
    centroid_y: float
    geometry: dict[str, Any]  # GeoJSON geometry
    area_sq_meters: float | None = None
    
    # Classification
    anomaly_type: AnomalyType = AnomalyType.UNKNOWN
    
    # Scoring
    anomaly_probability: float = 0.0  # 0.0 to 1.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    qc_priority: float = 0.0  # 0.0 to 1.0 (higher = review first)
    
    # Explainability - the MOST IMPORTANT part
    explanation: dict[str, Any] = field(default_factory=dict)
    # Expected structure:
    # {
    #     "primary_reason": "High local z-score",
    #     "features": {
    #         "z_score": 4.5,
    #         "slope": 45.2,
    #         "roughness": 0.8,
    #         "isolation_score": 0.95
    #     },
    #     "thresholds": {
    #         "z_score_threshold": 3.0,
    #         "isolation_threshold": 0.5
    #     },
    #     "detector_flags": ["isolation_forest", "zscore"]
    # }
    
    # Context
    local_depth_mean: float | None = None
    local_depth_std: float | None = None
    neighbor_count: int | None = None
    
    # Review status
    review_decision: ReviewDecision = ReviewDecision.PENDING
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_geojson_feature(self) -> dict[str, Any]:
        """Convert to GeoJSON Feature for export."""
        return {
            "type": "Feature",
            "id": str(self.id),
            "geometry": self.geometry,
            "properties": {
                "anomaly_id": str(self.id),
                "run_id": str(self.run_id),
                "anomaly_type": self.anomaly_type.value,
                "anomaly_probability": round(self.anomaly_probability, 4),
                "confidence_level": self.confidence_level.value,
                "qc_priority": round(self.qc_priority, 4),
                "review_decision": self.review_decision.value,
                "explanation": self.explanation,
            }
        }


@dataclass
class ReviewLog:
    """
    Review decision log entry (append-only audit trail).
    
    This is immutable once created - represents a point-in-time decision.
    """
    id: UUID
    anomaly_id: UUID
    run_id: UUID
    
    # Decision
    decision: ReviewDecision
    comment: str | None = None
    
    # Reviewer info
    reviewer_id: UUID | None = None
    reviewer_username: str | None = None
    
    # Context at time of review
    model_version: str | None = None
    anomaly_score_at_review: float | None = None
    
    # Timestamp (immutable)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @staticmethod
    def create(
        anomaly_id: UUID,
        run_id: UUID,
        decision: ReviewDecision,
        reviewer_id: UUID,
        reviewer_username: str,
        comment: str | None = None,
        model_version: str | None = None,
        anomaly_score: float | None = None,
    ) -> "ReviewLog":
        """Factory method to create a new review log entry."""
        return ReviewLog(
            id=uuid4(),
            anomaly_id=anomaly_id,
            run_id=run_id,
            decision=decision,
            comment=comment,
            reviewer_id=reviewer_id,
            reviewer_username=reviewer_username,
            model_version=model_version,
            anomaly_score_at_review=anomaly_score,
            created_at=datetime.utcnow(),
        )


@dataclass
class AuditLogEntry:
    """
    General audit log entry for all significant actions.
    
    Append-only log for security and compliance.
    """
    id: UUID
    action: str  # e.g., "dataset.upload", "run.start", "review.submit"
    resource_type: str  # e.g., "dataset", "run", "anomaly"
    resource_id: UUID
    
    # Actor
    user_id: UUID | None = None
    username: str | None = None
    
    # Details
    details: dict[str, Any] = field(default_factory=dict)
    
    # Network info (for security)
    ip_address: str | None = None
    user_agent: str | None = None
    
    # Timestamp
    created_at: datetime = field(default_factory=datetime.utcnow)
