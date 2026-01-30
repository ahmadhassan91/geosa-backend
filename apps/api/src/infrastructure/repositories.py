"""
Repository Implementations

Concrete implementations of domain repository interfaces.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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
    UserRole,
)
from src.infrastructure.models import (
    AnomalyModel,
    DatasetModel,
    ModelRunModel,
    ReviewLogModel,
    UserModel,
)


class SQLAlchemyDatasetRepository:
    """Dataset repository using SQLAlchemy."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, dataset: Dataset) -> Dataset:
        """Create a new dataset."""
        model = DatasetModel(
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
            resolution_x=dataset.resolution[0] if dataset.resolution else None,
            resolution_y=dataset.resolution[1] if dataset.resolution else None,
            point_count=dataset.point_count,
            z_min=dataset.z_min,
            z_max=dataset.z_max,
            z_mean=dataset.z_mean,
            z_std=dataset.z_std,
            nodata_percentage=dataset.nodata_percentage,
            created_by=dataset.created_by,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)
    
    async def get_by_id(self, dataset_id: UUID) -> Dataset | None:
        """Get dataset by ID."""
        result = await self.session.execute(
            select(DatasetModel).where(DatasetModel.id == dataset_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def list_all(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[Dataset], int]:
        """List all datasets with pagination."""
        # Count total
        count_result = await self.session.execute(
            select(func.count(DatasetModel.id))
        )
        total = count_result.scalar_one()
        
        # Get page
        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(DatasetModel)
            .order_by(DatasetModel.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        models = result.scalars().all()
        
        return [self._to_entity(m) for m in models], total
    
    async def delete(self, dataset_id: UUID) -> bool:
        """Delete a dataset."""
        result = await self.session.execute(
            select(DatasetModel).where(DatasetModel.id == dataset_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            return True
        return False
    
    async def update_metadata(
        self, dataset_id: UUID, metadata: dict[str, Any]
    ) -> Dataset | None:
        """Update dataset metadata after processing."""
        result = await self.session.execute(
            select(DatasetModel).where(DatasetModel.id == dataset_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        
        for key, value in metadata.items():
            if hasattr(model, key):
                setattr(model, key, value)
        
        model.updated_at = datetime.utcnow()
        await self.session.flush()
        return self._to_entity(model)
    
    def _to_entity(self, model: DatasetModel) -> Dataset:
        """Convert ORM model to domain entity."""
        return Dataset(
            id=model.id,
            name=model.name,
            description=model.description,
            file_path=model.file_path,
            file_type=model.file_type,
            file_size_bytes=model.file_size_bytes,
            crs=model.crs,
            bounds=model.bounds,
            width=model.width,
            height=model.height,
            resolution=(model.resolution_x, model.resolution_y) if model.resolution_x else None,
            point_count=model.point_count,
            z_min=model.z_min,
            z_max=model.z_max,
            z_mean=model.z_mean,
            z_std=model.z_std,
            nodata_percentage=model.nodata_percentage,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyRunRepository:
    """Run repository using SQLAlchemy."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, run: ModelRun) -> ModelRun:
        """Create a new run."""
        model = ModelRunModel(
            id=run.id,
            dataset_id=run.dataset_id,
            status=run.status,
            config_hash=run.config_hash,
            config_snapshot=run.config_snapshot,
            model_version=run.model_version,
            created_by=run.created_by,
            created_at=run.created_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)
    
    async def get_by_id(self, run_id: UUID) -> ModelRun | None:
        """Get run by ID."""
        result = await self.session.execute(
            select(ModelRunModel).where(ModelRunModel.id == run_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def update(self, run: ModelRun) -> ModelRun:
        """Update a run."""
        await self.session.execute(
            update(ModelRunModel)
            .where(ModelRunModel.id == run.id)
            .values(
                status=run.status,
                started_at=run.started_at,
                completed_at=run.completed_at,
                total_anomalies=run.total_anomalies,
                high_confidence_count=run.high_confidence_count,
                medium_confidence_count=run.medium_confidence_count,
                low_confidence_count=run.low_confidence_count,
                heatmap_path=run.heatmap_path,
                geojson_path=run.geojson_path,
                report_path=run.report_path,
                error_message=run.error_message,
            )
        )
        await self.session.flush()
        return run
    
    async def list_by_dataset(
        self, dataset_id: UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[ModelRun], int]:
        """List runs for a dataset."""
        count_result = await self.session.execute(
            select(func.count(ModelRunModel.id)).where(
                ModelRunModel.dataset_id == dataset_id
            )
        )
        total = count_result.scalar_one()
        
        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(ModelRunModel)
            .where(ModelRunModel.dataset_id == dataset_id)
            .order_by(ModelRunModel.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        models = result.scalars().all()
        
        return [self._to_entity(m) for m in models], total
    
    async def list_all(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[ModelRun], int]:
        """List all runs."""
        count_result = await self.session.execute(
            select(func.count(ModelRunModel.id))
        )
        total = count_result.scalar_one()
        
        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(ModelRunModel)
            .order_by(ModelRunModel.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        models = result.scalars().all()
        
        return [self._to_entity(m) for m in models], total
    
    def _to_entity(self, model: ModelRunModel) -> ModelRun:
        """Convert ORM model to domain entity."""
        return ModelRun(
            id=model.id,
            dataset_id=model.dataset_id,
            status=model.status,
            config_hash=model.config_hash,
            config_snapshot=model.config_snapshot,
            model_version=model.model_version,
            started_at=model.started_at,
            completed_at=model.completed_at,
            total_anomalies=model.total_anomalies,
            high_confidence_count=model.high_confidence_count,
            medium_confidence_count=model.medium_confidence_count,
            low_confidence_count=model.low_confidence_count,
            heatmap_path=model.heatmap_path,
            geojson_path=model.geojson_path,
            report_path=model.report_path,
            error_message=model.error_message,
            created_by=model.created_by,
            created_at=model.created_at,
        )


class SQLAlchemyAnomalyRepository:
    """Anomaly repository using SQLAlchemy."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_batch(self, anomalies: list[Anomaly]) -> list[Anomaly]:
        """Create multiple anomalies at once."""
        models = [
            AnomalyModel(
                id=a.id,
                run_id=a.run_id,
                centroid_x=a.centroid_x,
                centroid_y=a.centroid_y,
                geometry=a.geometry,
                area_sq_meters=a.area_sq_meters,
                anomaly_type=a.anomaly_type,
                anomaly_probability=a.anomaly_probability,
                confidence_level=a.confidence_level,
                qc_priority=a.qc_priority,
                explanation=a.explanation,
                local_depth_mean=a.local_depth_mean,
                local_depth_std=a.local_depth_std,
                neighbor_count=a.neighbor_count,
                review_decision=a.review_decision,
                created_at=a.created_at,
            )
            for a in anomalies
        ]
        self.session.add_all(models)
        await self.session.flush()
        return anomalies
    
    async def get_by_id(self, anomaly_id: UUID) -> Anomaly | None:
        """Get anomaly by ID."""
        result = await self.session.execute(
            select(AnomalyModel).where(AnomalyModel.id == anomaly_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_by_run(
        self,
        run_id: UUID,
        page: int = 1,
        page_size: int = 20,
        confidence_filter: str | None = None,
        decision_filter: str | None = None,
        sort_by: str = "qc_priority",
        sort_desc: bool = True,
    ) -> tuple[list[Anomaly], int]:
        """Get anomalies for a run with filtering and sorting."""
        # Build base query
        query = select(AnomalyModel).where(AnomalyModel.run_id == run_id)
        count_query = select(func.count(AnomalyModel.id)).where(
            AnomalyModel.run_id == run_id
        )
        
        # Apply filters
        if confidence_filter:
            conf = ConfidenceLevel(confidence_filter)
            query = query.where(AnomalyModel.confidence_level == conf)
            count_query = count_query.where(AnomalyModel.confidence_level == conf)
        
        if decision_filter:
            if decision_filter.startswith("!"):
                # Exclude this decision
                dec = ReviewDecision(decision_filter[1:])
                query = query.where(AnomalyModel.review_decision != dec)
                count_query = count_query.where(AnomalyModel.review_decision != dec)
            else:
                dec = ReviewDecision(decision_filter)
                query = query.where(AnomalyModel.review_decision == dec)
                count_query = count_query.where(AnomalyModel.review_decision == dec)
        
        # Apply sorting
        sort_column = getattr(AnomalyModel, sort_by, AnomalyModel.qc_priority)
        if sort_desc:
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Get count
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        return [self._to_entity(m) for m in models], total
    
    async def update_decision(
        self, anomaly_id: UUID, decision: ReviewDecision
    ) -> Anomaly | None:
        """Update anomaly review decision."""
        await self.session.execute(
            update(AnomalyModel)
            .where(AnomalyModel.id == anomaly_id)
            .values(review_decision=decision)
        )
        await self.session.flush()
        return await self.get_by_id(anomaly_id)
    
    async def get_summary(self, run_id: UUID) -> dict[str, Any]:
        """Get summary statistics for a run's anomalies."""
        # By confidence
        conf_result = await self.session.execute(
            select(
                AnomalyModel.confidence_level,
                func.count(AnomalyModel.id),
            )
            .where(AnomalyModel.run_id == run_id)
            .group_by(AnomalyModel.confidence_level)
        )
        by_confidence = {row[0].value: row[1] for row in conf_result.all()}
        
        # By type
        type_result = await self.session.execute(
            select(
                AnomalyModel.anomaly_type,
                func.count(AnomalyModel.id),
            )
            .where(AnomalyModel.run_id == run_id)
            .group_by(AnomalyModel.anomaly_type)
        )
        by_type = {row[0].value: row[1] for row in type_result.all()}
        
        # By decision
        dec_result = await self.session.execute(
            select(
                AnomalyModel.review_decision,
                func.count(AnomalyModel.id),
            )
            .where(AnomalyModel.run_id == run_id)
            .group_by(AnomalyModel.review_decision)
        )
        by_decision = {row[0].value: row[1] for row in dec_result.all()}
        
        return {
            "by_confidence": by_confidence,
            "by_type": by_type,
            "by_decision": by_decision,
        }
    
    def _to_entity(self, model: AnomalyModel) -> Anomaly:
        """Convert ORM model to domain entity."""
        return Anomaly(
            id=model.id,
            run_id=model.run_id,
            centroid_x=model.centroid_x,
            centroid_y=model.centroid_y,
            geometry=model.geometry,
            area_sq_meters=model.area_sq_meters,
            anomaly_type=model.anomaly_type,
            anomaly_probability=model.anomaly_probability,
            confidence_level=model.confidence_level,
            qc_priority=model.qc_priority,
            explanation=model.explanation,
            local_depth_mean=model.local_depth_mean,
            local_depth_std=model.local_depth_std,
            neighbor_count=model.neighbor_count,
            review_decision=model.review_decision,
            created_at=model.created_at,
        )


class SQLAlchemyReviewLogRepository:
    """Review log repository using SQLAlchemy."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, log: ReviewLog) -> ReviewLog:
        """Create a new review log entry."""
        model = ReviewLogModel(
            id=log.id,
            anomaly_id=log.anomaly_id,
            run_id=log.run_id,
            decision=log.decision,
            comment=log.comment,
            reviewer_id=log.reviewer_id,
            reviewer_username=log.reviewer_username,
            model_version=log.model_version,
            anomaly_score_at_review=log.anomaly_score_at_review,
            created_at=log.created_at,
        )
        self.session.add(model)
        await self.session.flush()
        return log
    
    async def get_by_anomaly(self, anomaly_id: UUID) -> list[ReviewLog]:
        """Get all review logs for an anomaly."""
        result = await self.session.execute(
            select(ReviewLogModel)
            .where(ReviewLogModel.anomaly_id == anomaly_id)
            .order_by(ReviewLogModel.created_at.desc())
        )
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]
    
    async def get_by_run(self, run_id: UUID) -> list[ReviewLog]:
        """Get all review logs for a run."""
        result = await self.session.execute(
            select(ReviewLogModel)
            .where(ReviewLogModel.run_id == run_id)
            .order_by(ReviewLogModel.created_at.desc())
        )
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]
    
    def _to_entity(self, model: ReviewLogModel) -> ReviewLog:
        """Convert ORM model to domain entity."""
        return ReviewLog(
            id=model.id,
            anomaly_id=model.anomaly_id,
            run_id=model.run_id,
            decision=model.decision,
            comment=model.comment,
            reviewer_id=model.reviewer_id,
            reviewer_username=model.reviewer_username,
            model_version=model.model_version,
            anomaly_score_at_review=model.anomaly_score_at_review,
            created_at=model.created_at,
        )


class SQLAlchemyUserRepository:
    """User repository using SQLAlchemy."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, user: User) -> User:
        """Create a new user."""
        model = UserModel(
            id=user.id,
            username=user.username,
            email=user.email,
            hashed_password=user.hashed_password,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self.session.add(model)
        await self.session.flush()
        return user
    
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def list_all(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[User], int]:
        """List all users."""
        count_result = await self.session.execute(
            select(func.count(UserModel.id))
        )
        total = count_result.scalar_one()
        
        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(UserModel)
            .order_by(UserModel.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        models = result.scalars().all()
        
        return [self._to_entity(m) for m in models], total
    
    def _to_entity(self, model: UserModel) -> User:
        """Convert ORM model to domain entity."""
        return User(
            id=model.id,
            username=model.username,
            email=model.email,
            hashed_password=model.hashed_password,
            role=model.role,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
