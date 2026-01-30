"""
Application Use Cases

Business logic orchestration for HydroQ-QC-Assistant.
Each use case represents a single user action.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from src.domain.entities import (
    Anomaly,
    AnomalyType,
    ConfidenceLevel,
    Dataset,
    ModelRun,
    ReviewDecision,
    ReviewLog,
    RunStatus,
    User,
)


# =============================================================================
# Repository Interfaces (Ports)
# =============================================================================

class DatasetRepository(Protocol):
    """Port for dataset persistence."""
    
    async def create(self, dataset: Dataset) -> Dataset: ...
    async def get_by_id(self, dataset_id: UUID) -> Dataset | None: ...
    async def list_all(self, page: int, page_size: int) -> tuple[list[Dataset], int]: ...
    async def delete(self, dataset_id: UUID) -> bool: ...


class RunRepository(Protocol):
    """Port for run persistence."""
    
    async def create(self, run: ModelRun) -> ModelRun: ...
    async def get_by_id(self, run_id: UUID) -> ModelRun | None: ...
    async def update(self, run: ModelRun) -> ModelRun: ...
    async def list_by_dataset(self, dataset_id: UUID, page: int, page_size: int) -> tuple[list[ModelRun], int]: ...
    async def list_all(self, page: int, page_size: int) -> tuple[list[ModelRun], int]: ...


class AnomalyRepository(Protocol):
    """Port for anomaly persistence."""
    
    async def create_batch(self, anomalies: list[Anomaly]) -> list[Anomaly]: ...
    async def get_by_id(self, anomaly_id: UUID) -> Anomaly | None: ...
    async def get_by_run(
        self, 
        run_id: UUID, 
        page: int, 
        page_size: int,
        confidence_filter: str | None = None,
        decision_filter: str | None = None,
        sort_by: str = "qc_priority",
        sort_desc: bool = True,
    ) -> tuple[list[Anomaly], int]: ...
    async def update_decision(self, anomaly_id: UUID, decision: ReviewDecision) -> Anomaly | None: ...
    async def get_summary(self, run_id: UUID) -> dict[str, Any]: ...


class ReviewLogRepository(Protocol):
    """Port for review log persistence."""
    
    async def create(self, log: ReviewLog) -> ReviewLog: ...
    async def get_by_anomaly(self, anomaly_id: UUID) -> list[ReviewLog]: ...
    async def get_by_run(self, run_id: UUID) -> list[ReviewLog]: ...


class FileStore(Protocol):
    """Port for file storage."""
    
    async def save_upload(self, filename: str, content: bytes) -> str: ...
    async def save_output(self, run_id: UUID, filename: str, content: bytes) -> str: ...
    async def get_path(self, relative_path: str) -> str: ...
    async def delete(self, path: str) -> bool: ...


class MLPipeline(Protocol):
    """Port for ML processing pipeline."""
    
    async def run_analysis(
        self,
        dataset: Dataset,
        config: dict[str, Any],
        progress_callback: callable | None = None,
    ) -> tuple[list[Anomaly], dict[str, str]]: ...


# =============================================================================
# Use Cases
# =============================================================================

class CreateDataset:
    """Use case: Upload and register a new dataset."""
    
    def __init__(
        self,
        dataset_repo: DatasetRepository,
        file_store: FileStore,
    ):
        self.dataset_repo = dataset_repo
        self.file_store = file_store
    
    async def execute(
        self,
        name: str,
        description: str,
        filename: str,
        content: bytes,
        user_id: UUID,
    ) -> Dataset:
        """
        Upload a new dataset file and extract metadata.
        
        Args:
            name: Human-readable name
            description: Optional description
            filename: Original filename
            content: File bytes
            user_id: ID of uploading user
            
        Returns:
            Created Dataset entity
        """
        # Determine file type
        file_type = self._detect_file_type(filename)
        
        # Save file
        file_path = await self.file_store.save_upload(filename, content)
        
        # Create dataset entity
        dataset = Dataset(
            id=uuid4(),
            name=name,
            description=description,
            file_path=file_path,
            file_type=file_type,
            file_size_bytes=len(content),
            created_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        # TODO: Extract metadata (CRS, bounds, stats) from file
        # This will be done by infrastructure layer
        
        # Persist
        return await self.dataset_repo.create(dataset)
    
    def _detect_file_type(self, filename: str) -> str:
        """Detect file type from extension."""
        lower = filename.lower()
        if lower.endswith((".tif", ".tiff", ".geotiff")):
            return "geotiff"
        elif lower.endswith(".csv"):
            return "csv"
        elif lower.endswith(".parquet"):
            return "parquet"
        else:
            raise ValueError(f"Unsupported file type: {filename}")


class StartAnalysisRun:
    """Use case: Start a new analysis run on a dataset."""
    
    MODEL_VERSION = "0.1.0"
    
    def __init__(
        self,
        run_repo: RunRepository,
        dataset_repo: DatasetRepository,
        anomaly_repo: AnomalyRepository,
        ml_pipeline: MLPipeline,
        file_store: FileStore,
        config: dict[str, Any],
    ):
        self.run_repo = run_repo
        self.dataset_repo = dataset_repo
        self.anomaly_repo = anomaly_repo
        self.ml_pipeline = ml_pipeline
        self.file_store = file_store
        self.config = config
    
    async def execute(
        self,
        dataset_id: UUID,
        user_id: UUID,
        config_overrides: dict[str, Any] | None = None,
    ) -> ModelRun:
        """
        Start analysis on a dataset.
        
        Args:
            dataset_id: ID of dataset to analyze
            user_id: ID of user starting the run
            config_overrides: Optional config overrides
            
        Returns:
            Created ModelRun entity (status=pending)
        """
        # Get dataset
        dataset = await self.dataset_repo.get_by_id(dataset_id)
        if dataset is None:
            raise ValueError(f"Dataset not found: {dataset_id}")
        
        # Merge config
        effective_config = {**self.config}
        if config_overrides:
            effective_config = self._merge_config(effective_config, config_overrides)
        
        # Create config hash for reproducibility
        config_hash = self._hash_config(effective_config)
        
        # Create run entity
        run = ModelRun(
            id=uuid4(),
            dataset_id=dataset_id,
            status=RunStatus.PENDING,
            config_hash=config_hash,
            config_snapshot=effective_config,
            model_version=self.MODEL_VERSION,
            created_by=user_id,
            created_at=datetime.utcnow(),
        )
        
        # Persist
        run = await self.run_repo.create(run)
        
        # NOTE: Actual processing is triggered asynchronously
        # This use case only creates the run record
        
        return run
    
    def _merge_config(self, base: dict, overrides: dict) -> dict:
        """Deep merge config overrides."""
        result = base.copy()
        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def _hash_config(self, config: dict) -> str:
        """Generate deterministic hash of config."""
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]


class GetRunAnomalies:
    """Use case: Get paginated anomalies for a run."""
    
    def __init__(self, anomaly_repo: AnomalyRepository):
        self.anomaly_repo = anomaly_repo
    
    async def execute(
        self,
        run_id: UUID,
        page: int = 1,
        page_size: int = 20,
        confidence_filter: str | None = None,
        decision_filter: str | None = None,
        sort_by: str = "qc_priority",
        sort_desc: bool = True,
    ) -> tuple[list[Anomaly], int, dict[str, Any]]:
        """
        Get anomalies for a run with filtering and sorting.
        
        Returns:
            Tuple of (anomalies, total_count, summary_stats)
        """
        anomalies, total = await self.anomaly_repo.get_by_run(
            run_id=run_id,
            page=page,
            page_size=page_size,
            confidence_filter=confidence_filter,
            decision_filter=decision_filter,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )
        
        summary = await self.anomaly_repo.get_summary(run_id)
        
        return anomalies, total, summary


class SubmitReview:
    """Use case: Submit a review decision for an anomaly."""
    
    def __init__(
        self,
        anomaly_repo: AnomalyRepository,
        review_log_repo: ReviewLogRepository,
        run_repo: RunRepository,
    ):
        self.anomaly_repo = anomaly_repo
        self.review_log_repo = review_log_repo
        self.run_repo = run_repo
    
    async def execute(
        self,
        anomaly_id: UUID,
        decision: str,
        comment: str | None,
        reviewer: User,
    ) -> tuple[Anomaly, ReviewLog]:
        """
        Submit a review decision.
        
        Args:
            anomaly_id: ID of anomaly to review
            decision: "accepted" or "rejected"
            comment: Optional reviewer comment
            reviewer: User submitting the review
            
        Returns:
            Tuple of (updated Anomaly, ReviewLog entry)
        """
        # Validate permission
        if not reviewer.can_review():
            raise PermissionError("User cannot submit reviews")
        
        # Get anomaly
        anomaly = await self.anomaly_repo.get_by_id(anomaly_id)
        if anomaly is None:
            raise ValueError(f"Anomaly not found: {anomaly_id}")
        
        # Get run for model version
        run = await self.run_repo.get_by_id(anomaly.run_id)
        
        # Parse decision
        review_decision = ReviewDecision(decision)
        
        # Update anomaly
        updated_anomaly = await self.anomaly_repo.update_decision(
            anomaly_id=anomaly_id,
            decision=review_decision,
        )
        
        # Create audit log
        review_log = ReviewLog.create(
            anomaly_id=anomaly_id,
            run_id=anomaly.run_id,
            decision=review_decision,
            reviewer_id=reviewer.id,
            reviewer_username=reviewer.username,
            comment=comment,
            model_version=run.model_version if run else None,
            anomaly_score=anomaly.anomaly_probability,
        )
        
        review_log = await self.review_log_repo.create(review_log)
        
        return updated_anomaly, review_log


class ExportRunReport:
    """Use case: Export run results in various formats."""
    
    def __init__(
        self,
        run_repo: RunRepository,
        dataset_repo: DatasetRepository,
        anomaly_repo: AnomalyRepository,
        file_store: FileStore,
    ):
        self.run_repo = run_repo
        self.dataset_repo = dataset_repo
        self.anomaly_repo = anomaly_repo
        self.file_store = file_store
    
    async def execute(
        self,
        run_id: UUID,
        format: str = "json",
        include_reviewed_only: bool = False,
    ) -> tuple[str, str, int]:
        """
        Export run results.
        
        Args:
            run_id: ID of run to export
            format: "json", "geojson", or "pdf"
            include_reviewed_only: Only include reviewed anomalies
            
        Returns:
            Tuple of (file_path, filename, file_size)
        """
        # Get run and dataset
        run = await self.run_repo.get_by_id(run_id)
        if run is None:
            raise ValueError(f"Run not found: {run_id}")
        
        dataset = await self.dataset_repo.get_by_id(run.dataset_id)
        
        # Get all anomalies (no pagination for export)
        decision_filter = None
        if include_reviewed_only:
            decision_filter = "!pending"  # Not pending = reviewed
        
        anomalies, _ = await self.anomaly_repo.get_by_run(
            run_id=run_id,
            page=1,
            page_size=10000,  # Get all
            decision_filter=decision_filter,
        )
        
        # Generate export
        if format == "json":
            content, filename = self._export_json(run, dataset, anomalies)
        elif format == "geojson":
            content, filename = self._export_geojson(run, anomalies)
        elif format == "pdf":
            content, filename = await self._export_pdf(run, dataset, anomalies)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Save to file store
        file_path = await self.file_store.save_output(run_id, filename, content)
        
        return file_path, filename, len(content)
    
    def _export_json(
        self, 
        run: ModelRun, 
        dataset: Dataset | None, 
        anomalies: list[Anomaly]
    ) -> tuple[bytes, str]:
        """Export as JSON report."""
        report = {
            "run": {
                "id": str(run.id),
                "dataset_id": str(run.dataset_id),
                "status": run.status.value,
                "model_version": run.model_version,
                "config_hash": run.config_hash,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "total_anomalies": run.total_anomalies,
            },
            "dataset": {
                "name": dataset.name if dataset else None,
                "file_type": dataset.file_type if dataset else None,
            },
            "anomalies": [
                {
                    "id": str(a.id),
                    "centroid": [a.centroid_x, a.centroid_y],
                    "type": a.anomaly_type.value,
                    "probability": a.anomaly_probability,
                    "confidence": a.confidence_level.value,
                    "priority": a.qc_priority,
                    "decision": a.review_decision.value,
                    "explanation": a.explanation,
                }
                for a in anomalies
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        content = json.dumps(report, indent=2).encode("utf-8")
        filename = f"run_{run.id}_report.json"
        
        return content, filename
    
    def _export_geojson(
        self, 
        run: ModelRun, 
        anomalies: list[Anomaly]
    ) -> tuple[bytes, str]:
        """Export anomalies as GeoJSON FeatureCollection."""
        geojson = {
            "type": "FeatureCollection",
            "features": [a.to_geojson_feature() for a in anomalies],
            "properties": {
                "run_id": str(run.id),
                "model_version": run.model_version,
                "generated_at": datetime.utcnow().isoformat(),
            },
        }
        
        content = json.dumps(geojson, indent=2).encode("utf-8")
        filename = f"run_{run.id}_anomalies.geojson"
        
        return content, filename
    
    async def _export_pdf(
        self, 
        run: ModelRun, 
        dataset: Dataset | None, 
        anomalies: list[Anomaly]
    ) -> tuple[bytes, str]:
        """Export as PDF report."""
        # TODO: Implement PDF generation with reportlab or weasyprint
        raise NotImplementedError("PDF export not yet implemented")
