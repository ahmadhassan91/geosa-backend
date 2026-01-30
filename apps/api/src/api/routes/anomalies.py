"""
Anomaly Routes

API endpoints for anomaly management and review.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.api.dependencies import CurrentUser, DbSession, HydrographerUser
from src.application.dtos import (
    AnomalyResponse,
    AnomalyListResponse,
    ReviewSubmit,
    ReviewResponse,
    ReviewListResponse,
    BulkReviewSubmit,
)
from src.domain.entities import Anomaly, ReviewDecision, ReviewLog
from src.infrastructure.repositories import (
    SQLAlchemyAnomalyRepository,
    SQLAlchemyReviewLogRepository,
    SQLAlchemyRunRepository,
)

router = APIRouter(prefix="/runs/{run_id}/anomalies", tags=["anomalies"])


@router.get("", response_model=AnomalyListResponse)
async def list_anomalies(
    run_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = 1,
    page_size: int = 20,
    confidence: str | None = None,
    decision: str | None = None,
    sort_by: str = "qc_priority",
    sort_desc: bool = True,
):
    """
    List anomalies for a run with filtering and sorting.
    
    Filters:
    - confidence: low, medium, high
    - decision: pending, accepted, rejected
    
    Sort options:
    - qc_priority (default)
    - anomaly_probability
    - created_at
    """
    # Verify run exists
    run_repo = SQLAlchemyRunRepository(db)
    run = await run_repo.get_by_id(run_id)
    
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )
    
    anomaly_repo = SQLAlchemyAnomalyRepository(db)
    
    anomalies, total = await anomaly_repo.get_by_run(
        run_id=run_id,
        page=page,
        page_size=page_size,
        confidence_filter=confidence,
        decision_filter=decision,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )
    
    # Get summary stats
    summary = await anomaly_repo.get_summary(run_id)
    
    return AnomalyListResponse(
        items=[_to_response(a) for a in anomalies],
        total=total,
        page=page,
        page_size=page_size,
        by_confidence=summary.get("by_confidence", {}),
        by_type=summary.get("by_type", {}),
        by_decision=summary.get("by_decision", {}),
    )


@router.get("/{anomaly_id}", response_model=AnomalyResponse)
async def get_anomaly(
    run_id: UUID,
    anomaly_id: UUID,
    db: DbSession,
    user: CurrentUser,
):
    """Get a specific anomaly by ID with full explanation."""
    anomaly_repo = SQLAlchemyAnomalyRepository(db)
    anomaly = await anomaly_repo.get_by_id(anomaly_id)
    
    if anomaly is None or anomaly.run_id != run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly not found: {anomaly_id}",
        )
    
    return _to_response(anomaly)


@router.post("/{anomaly_id}/review", response_model=ReviewResponse)
async def submit_review(
    run_id: UUID,
    anomaly_id: UUID,
    request: ReviewSubmit,
    db: DbSession,
    user: HydrographerUser,
):
    """
    Submit a review decision for an anomaly.
    
    Decisions:
    - accepted: Confirm this is a real anomaly that needs attention
    - rejected: Mark as false positive
    
    All decisions are logged in an immutable audit trail.
    """
    anomaly_repo = SQLAlchemyAnomalyRepository(db)
    review_log_repo = SQLAlchemyReviewLogRepository(db)
    run_repo = SQLAlchemyRunRepository(db)
    
    # Get anomaly
    anomaly = await anomaly_repo.get_by_id(anomaly_id)
    
    if anomaly is None or anomaly.run_id != run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly not found: {anomaly_id}",
        )
    
    # Get run for model version
    run = await run_repo.get_by_id(run_id)
    
    # Parse decision
    try:
        decision = ReviewDecision(request.decision)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision: {request.decision}. Must be 'accepted' or 'rejected'.",
        )
    
    # Update anomaly decision
    updated_anomaly = await anomaly_repo.update_decision(anomaly_id, decision)
    
    # Create audit log entry
    review_log = ReviewLog.create(
        anomaly_id=anomaly_id,
        run_id=run_id,
        decision=decision,
        reviewer_id=user.id,
        reviewer_username=user.username,
        comment=request.comment,
        model_version=run.model_version if run else None,
        anomaly_score=anomaly.anomaly_probability,
    )
    
    created_log = await review_log_repo.create(review_log)
    
    return _log_to_response(created_log)


@router.post("/bulk-review", response_model=list[ReviewResponse])
async def bulk_review(
    run_id: UUID,
    request: BulkReviewSubmit,
    db: DbSession,
    user: HydrographerUser,
):
    """
    Submit review decisions for multiple anomalies at once.
    
    Useful for batch processing of similar anomalies.
    """
    anomaly_repo = SQLAlchemyAnomalyRepository(db)
    review_log_repo = SQLAlchemyReviewLogRepository(db)
    run_repo = SQLAlchemyRunRepository(db)
    
    # Get run for model version
    run = await run_repo.get_by_id(run_id)
    
    # Parse decision
    try:
        decision = ReviewDecision(request.decision)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision: {request.decision}. Must be 'accepted' or 'rejected'.",
        )
    
    results = []
    
    for anomaly_id in request.anomaly_ids:
        # Get anomaly
        anomaly = await anomaly_repo.get_by_id(anomaly_id)
        
        if anomaly is None or anomaly.run_id != run_id:
            continue  # Skip invalid anomalies in bulk operation
        
        # Update anomaly decision
        await anomaly_repo.update_decision(anomaly_id, decision)
        
        # Create audit log entry
        review_log = ReviewLog.create(
            anomaly_id=anomaly_id,
            run_id=run_id,
            decision=decision,
            reviewer_id=user.id,
            reviewer_username=user.username,
            comment=request.comment,
            model_version=run.model_version if run else None,
            anomaly_score=anomaly.anomaly_probability,
        )
        
        created_log = await review_log_repo.create(review_log)
        results.append(_log_to_response(created_log))
    
    return results


@router.get("/{anomaly_id}/history", response_model=ReviewListResponse)
async def get_review_history(
    run_id: UUID,
    anomaly_id: UUID,
    db: DbSession,
    user: CurrentUser,
):
    """Get the full review history for an anomaly."""
    anomaly_repo = SQLAlchemyAnomalyRepository(db)
    review_log_repo = SQLAlchemyReviewLogRepository(db)
    
    # Verify anomaly exists
    anomaly = await anomaly_repo.get_by_id(anomaly_id)
    
    if anomaly is None or anomaly.run_id != run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly not found: {anomaly_id}",
        )
    
    logs = await review_log_repo.get_by_anomaly(anomaly_id)
    
    return ReviewListResponse(
        items=[_log_to_response(log) for log in logs],
        total=len(logs),
    )


def _to_response(anomaly: Anomaly) -> AnomalyResponse:
    """Convert domain entity to response DTO."""
    return AnomalyResponse(
        id=anomaly.id,
        run_id=anomaly.run_id,
        centroid_x=anomaly.centroid_x,
        centroid_y=anomaly.centroid_y,
        geometry=anomaly.geometry,
        area_sq_meters=anomaly.area_sq_meters,
        anomaly_type=anomaly.anomaly_type.value,
        anomaly_probability=anomaly.anomaly_probability,
        confidence_level=anomaly.confidence_level.value,
        qc_priority=anomaly.qc_priority,
        explanation=anomaly.explanation,
        local_depth_mean=anomaly.local_depth_mean,
        local_depth_std=anomaly.local_depth_std,
        neighbor_count=anomaly.neighbor_count,
        review_decision=anomaly.review_decision.value,
        created_at=anomaly.created_at,
    )


def _log_to_response(log: ReviewLog) -> ReviewResponse:
    """Convert review log to response DTO."""
    return ReviewResponse(
        id=log.id,
        anomaly_id=log.anomaly_id,
        run_id=log.run_id,
        decision=log.decision.value,
        comment=log.comment,
        reviewer_id=log.reviewer_id,
        reviewer_username=log.reviewer_username,
        model_version=log.model_version,
        created_at=log.created_at,
    )
