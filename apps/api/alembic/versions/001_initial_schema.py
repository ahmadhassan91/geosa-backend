"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    user_role = postgresql.ENUM('admin', 'hydrographer', 'viewer', name='user_role', create_type=False)
    user_role.create(op.get_bind(), checkfirst=True)
    
    run_status = postgresql.ENUM('pending', 'processing', 'completed', 'failed', name='run_status', create_type=False)
    run_status.create(op.get_bind(), checkfirst=True)
    
    confidence_level = postgresql.ENUM('low', 'medium', 'high', name='confidence_level', create_type=False)
    confidence_level.create(op.get_bind(), checkfirst=True)
    
    review_decision = postgresql.ENUM('pending', 'accepted', 'rejected', name='review_decision', create_type=False)
    review_decision.create(op.get_bind(), checkfirst=True)
    
    anomaly_type = postgresql.ENUM('spike', 'hole', 'seam', 'noise_band', 'discontinuity', 'density_gap', 'unknown', name='anomaly_type', create_type=False)
    anomaly_type.create(op.get_bind(), checkfirst=True)
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', user_role, nullable=False, default='viewer'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Datasets table
    op.create_table(
        'datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), default=''),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(20), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('crs', sa.String(50)),
        sa.Column('bounds', postgresql.JSON()),
        sa.Column('width', sa.Integer()),
        sa.Column('height', sa.Integer()),
        sa.Column('resolution_x', sa.Float()),
        sa.Column('resolution_y', sa.Float()),
        sa.Column('point_count', sa.Integer()),
        sa.Column('z_min', sa.Float()),
        sa.Column('z_max', sa.Float()),
        sa.Column('z_mean', sa.Float()),
        sa.Column('z_std', sa.Float()),
        sa.Column('nodata_percentage', sa.Float()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Model runs table
    op.create_table(
        'model_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('datasets.id'), nullable=False, index=True),
        sa.Column('status', run_status, nullable=False, default='pending', index=True),
        sa.Column('config_hash', sa.String(32), nullable=False),
        sa.Column('config_snapshot', postgresql.JSON(), nullable=False, default={}),
        sa.Column('model_version', sa.String(20), nullable=False),
        sa.Column('started_at', sa.DateTime()),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('total_anomalies', sa.Integer(), default=0),
        sa.Column('high_confidence_count', sa.Integer(), default=0),
        sa.Column('medium_confidence_count', sa.Integer(), default=0),
        sa.Column('low_confidence_count', sa.Integer(), default=0),
        sa.Column('heatmap_path', sa.String(500)),
        sa.Column('geojson_path', sa.String(500)),
        sa.Column('report_path', sa.String(500)),
        sa.Column('error_message', sa.Text()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    
    # Anomalies table
    op.create_table(
        'anomalies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('model_runs.id'), nullable=False, index=True),
        sa.Column('centroid_x', sa.Float(), nullable=False),
        sa.Column('centroid_y', sa.Float(), nullable=False),
        sa.Column('geometry', postgresql.JSON(), nullable=False),
        sa.Column('area_sq_meters', sa.Float()),
        sa.Column('anomaly_type', anomaly_type, nullable=False, default='unknown'),
        sa.Column('anomaly_probability', sa.Float(), nullable=False, index=True),
        sa.Column('confidence_level', confidence_level, nullable=False, default='low', index=True),
        sa.Column('qc_priority', sa.Float(), nullable=False, index=True),
        sa.Column('explanation', postgresql.JSON(), nullable=False, default={}),
        sa.Column('local_depth_mean', sa.Float()),
        sa.Column('local_depth_std', sa.Float()),
        sa.Column('neighbor_count', sa.Integer()),
        sa.Column('review_decision', review_decision, nullable=False, default='pending', index=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    
    # Review logs table (append-only audit trail)
    op.create_table(
        'review_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('anomaly_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('anomalies.id'), nullable=False, index=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('model_runs.id'), nullable=False, index=True),
        sa.Column('decision', review_decision, nullable=False),
        sa.Column('comment', sa.Text()),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('reviewer_username', sa.String(50)),
        sa.Column('model_version', sa.String(20)),
        sa.Column('anomaly_score_at_review', sa.Float()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), index=True),
    )
    
    # Audit logs table (general audit trail)
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('action', sa.String(100), nullable=False, index=True),
        sa.Column('resource_type', sa.String(50), nullable=False, index=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('username', sa.String(50)),
        sa.Column('details', postgresql.JSON(), default={}),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('review_logs')
    op.drop_table('anomalies')
    op.drop_table('model_runs')
    op.drop_table('datasets')
    op.drop_table('users')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS anomaly_type')
    op.execute('DROP TYPE IF EXISTS review_decision')
    op.execute('DROP TYPE IF EXISTS confidence_level')
    op.execute('DROP TYPE IF EXISTS run_status')
    op.execute('DROP TYPE IF EXISTS user_role')
