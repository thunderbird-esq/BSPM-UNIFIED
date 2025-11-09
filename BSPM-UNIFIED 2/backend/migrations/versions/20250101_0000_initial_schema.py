"""Initial schema

Revision ID: initial_schema
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('username', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(255), nullable=True, unique=True, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, default='user'),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(512), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
    )

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('session_id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token', sa.String(512), nullable=False, unique=True, index=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
    )
    op.create_index('idx_session_user_active', 'sessions', ['user_id', 'is_active'])
    op.create_index('idx_session_expires', 'sessions', ['expires_at'])

    # Create generation_history table (must be before assets for foreign key)
    op.create_table(
        'generation_history',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('input_prompt', sa.Text(), nullable=False),
        sa.Column('input_parameters', postgresql.JSON(), nullable=True),
        sa.Column('output_path', sa.String(512), nullable=True),
        sa.Column('output_metadata', postgresql.JSON(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('cost_credits', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
    )
    op.create_index('idx_generation_user_created', 'generation_history', ['user_id', 'created_at'])
    op.create_index('idx_generation_status', 'generation_history', ['status'])
    op.create_index('idx_generation_type', 'generation_history', ['asset_type'])

    # Create sprites table
    op.create_table(
        'sprites',
        sa.Column('sprite_id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('thumbnail_path', sa.String(512), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('format', sa.String(50), nullable=True),
        sa.Column('generation_id', sa.String(36), sa.ForeignKey('generation_history.id'), nullable=True),
        sa.Column('style_preset', sa.String(100), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('negative_prompt', sa.Text(), nullable=True),
        sa.Column('seed', sa.Integer(), nullable=True),
        sa.Column('tags', postgresql.JSON(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
    )
    op.create_index('idx_sprite_user_created', 'sprites', ['user_id', 'created_at'])
    op.create_index('idx_sprite_category', 'sprites', ['category'])

    # Create music_tracks table
    op.create_table(
        'music_tracks',
        sa.Column('track_id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('format', sa.String(50), nullable=True),
        sa.Column('tempo', sa.Integer(), nullable=True),
        sa.Column('key_signature', sa.String(10), nullable=True),
        sa.Column('generation_id', sa.String(36), sa.ForeignKey('generation_history.id'), nullable=True),
        sa.Column('style', sa.String(100), nullable=True),
        sa.Column('mood', sa.String(100), nullable=True),
        sa.Column('tags', postgresql.JSON(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
    )
    op.create_index('idx_music_user_created', 'music_tracks', ['user_id', 'created_at'])
    op.create_index('idx_music_category', 'music_tracks', ['category'])

    # Create sound_effects table
    op.create_table(
        'sound_effects',
        sa.Column('sfx_id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('format', sa.String(50), nullable=True),
        sa.Column('sample_rate', sa.Integer(), nullable=True),
        sa.Column('generation_id', sa.String(36), sa.ForeignKey('generation_history.id'), nullable=True),
        sa.Column('effect_type', sa.String(100), nullable=True),
        sa.Column('tags', postgresql.JSON(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
    )
    op.create_index('idx_sfx_user_created', 'sound_effects', ['user_id', 'created_at'])
    op.create_index('idx_sfx_category', 'sound_effects', ['category'])

    # Create scripts table
    op.create_table(
        'scripts',
        sa.Column('script_id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('events', postgresql.JSON(), nullable=False),
        sa.Column('script_type', sa.String(100), nullable=True),
        sa.Column('complexity_score', sa.Integer(), nullable=True),
        sa.Column('generation_id', sa.String(36), sa.ForeignKey('generation_history.id'), nullable=True),
        sa.Column('tags', postgresql.JSON(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
    )
    op.create_index('idx_script_user_created', 'scripts', ['user_id', 'created_at'])
    op.create_index('idx_script_type', 'scripts', ['script_type'])

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(255), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.String(36), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(512), nullable=True),
        sa.Column('endpoint', sa.String(512), nullable=True),
        sa.Column('method', sa.String(10), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, index=True),
        sa.Column('details', postgresql.JSON(), nullable=True),
    )
    op.create_index('idx_audit_user_timestamp', 'audit_logs', ['user_id', 'timestamp'])
    op.create_index('idx_audit_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('audit_logs')
    op.drop_table('scripts')
    op.drop_table('sound_effects')
    op.drop_table('music_tracks')
    op.drop_table('sprites')
    op.drop_table('generation_history')
    op.drop_table('sessions')
    op.drop_table('users')
