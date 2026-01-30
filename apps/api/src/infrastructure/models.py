"""
SQLAlchemy ORM Models

Database models for HydroQ-QC-Assistant.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.entities import (
    ConfidenceLevel,
    ReviewDecision,
    RunStatus,
    UserRole,
    AnomalyType,
)
from src.infrastructure.database import Base


class UserModel(Base):
    """User database model."""
    
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=UserRole.VIEWER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    datasets: Mapped[list["DatasetModel"]] = relationship(back_populates="creator")
    runs: Mapped[list["ModelRunModel"]] = relationship(back_populates="creator")


class DatasetModel(Base):
    """Dataset database model."""
    
    __tablename__ = "datasets"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # geotiff, csv, parquet
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Spatial metadata
    crs: Mapped[str | None] = mapped_column(String(50))
    bounds: Mapped[dict | None] = mapped_column(JSON)  # {minx, miny, maxx, maxy}
    
    # Raster-specific
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    resolution_x: Mapped[float | None] = mapped_column(Float)
    resolution_y: Mapped[float | None] = mapped_column(Float)
    
    # Point-specific
    point_count: Mapped[int | None] = mapped_column(Integer)
    
    # Statistics
    z_min: Mapped[float | None] = mapped_column(Float)
    z_max: Mapped[float | None] = mapped_column(Float)
    z_mean: Mapped[float | None] = mapped_column(Float)
    z_std: Mapped[float | None] = mapped_column(Float)
    nodata_percentage: Mapped[float | None] = mapped_column(Float)
    
    # Timestamps and ownership
    created_by: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    creator: Mapped["UserModel | None"] = relationship(back_populates="datasets")
    runs: Mapped[list["ModelRunModel"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class ModelRunModel(Base):
    """Analysis run database model."""
    
    __tablename__ = "model_runs"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False, index=True
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=RunStatus.PENDING,
        index=True,
    )
    
    # Configuration for reproducibility
    config_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    config_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    
    # Results summary
    total_anomalies: Mapped[int] = mapped_column(Integer, default=0)
    high_confidence_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_confidence_count: Mapped[int] = mapped_column(Integer, default=0)
    low_confidence_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Output paths
    heatmap_path: Mapped[str | None] = mapped_column(String(500))
    geojson_path: Mapped[str | None] = mapped_column(String(500))
    report_path: Mapped[str | None] = mapped_column(String(500))
    
    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text)
    
    # Timestamps and ownership
    created_by: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    dataset: Mapped["DatasetModel"] = relationship(back_populates="runs")
    creator: Mapped["UserModel | None"] = relationship(back_populates="runs")
    anomalies: Mapped[list["AnomalyModel"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class AnomalyModel(Base):
    """Detected anomaly database model."""
    
    __tablename__ = "anomalies"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_runs.id"), nullable=False, index=True
    )
    
    # Spatial location
    centroid_x: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_y: Mapped[float] = mapped_column(Float, nullable=False)
    geometry: Mapped[dict] = mapped_column(JSON, nullable=False)  # GeoJSON geometry
    area_sq_meters: Mapped[float | None] = mapped_column(Float)
    
    # Classification
    anomaly_type: Mapped[AnomalyType] = mapped_column(
        Enum(AnomalyType, name="anomaly_type", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=AnomalyType.UNKNOWN,
    )
    
    # Scoring
    anomaly_probability: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    confidence_level: Mapped[ConfidenceLevel] = mapped_column(
        Enum(ConfidenceLevel, name="confidence_level", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=ConfidenceLevel.LOW,
        index=True,
    )
    qc_priority: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    
    # Explainability
    explanation: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    # Context
    local_depth_mean: Mapped[float | None] = mapped_column(Float)
    local_depth_std: Mapped[float | None] = mapped_column(Float)
    neighbor_count: Mapped[int | None] = mapped_column(Integer)
    
    # Review status
    review_decision: Mapped[ReviewDecision] = mapped_column(
        Enum(ReviewDecision, name="review_decision", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=ReviewDecision.PENDING,
        index=True,
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    run: Mapped["ModelRunModel"] = relationship(back_populates="anomalies")
    review_logs: Mapped[list["ReviewLogModel"]] = relationship(back_populates="anomaly", cascade="all, delete-orphan")


class ReviewLogModel(Base):
    """Review decision log (append-only audit trail)."""
    
    __tablename__ = "review_logs"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    anomaly_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("anomalies.id"), nullable=False, index=True
    )
    run_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_runs.id"), nullable=False, index=True
    )
    
    # Decision
    decision: Mapped[ReviewDecision] = mapped_column(
        Enum(ReviewDecision, name="review_decision", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text)
    
    # Reviewer info
    reviewer_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewer_username: Mapped[str | None] = mapped_column(String(50))
    
    # Context at time of review
    model_version: Mapped[str | None] = mapped_column(String(20))
    anomaly_score_at_review: Mapped[float | None] = mapped_column(Float)
    
    # Timestamp (immutable)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    anomaly: Mapped["AnomalyModel"] = relationship(back_populates="review_logs")


class AuditLogModel(Base):
    """General audit log (append-only)."""
    
    __tablename__ = "audit_logs"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    
    # Actor
    user_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True))
    username: Mapped[str | None] = mapped_column(String(50))
    
    # Details
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Network info
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
