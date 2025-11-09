"""
GBStudio Automation Hub - Database Models
SQLAlchemy ORM models for PostgreSQL

Models:
- User: User accounts and authentication
- Session: User sessions and tokens
- Sprite: Generated sprite assets
- MusicTrack: Generated music assets
- SoundEffect: Generated sound effects
- Script: GB Studio script assets
- GenerationHistory: Asset generation tracking
- AuditLog: System audit trail
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    JSON,
    Text,
    ForeignKey,
    Boolean,
    Float,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
import enum

from backend.database import Base


# ============================================================================
# Enums
# ============================================================================

class UserRole(str, enum.Enum):
    """User role types"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class AssetType(str, enum.Enum):
    """Asset generation types"""
    SPRITE = "sprite"
    MUSIC = "music"
    SFX = "sfx"
    SCRIPT = "script"


class GenerationStatus(str, enum.Enum):
    """Asset generation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# User Models
# ============================================================================

class User(Base):
    """User account model"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)

    # Profile
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(512), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    # Metadata
    metadata = Column(JSON, default=dict, nullable=True)

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    sprites = relationship("Sprite", back_populates="user", cascade="all, delete-orphan")
    music_tracks = relationship("MusicTrack", back_populates="user", cascade="all, delete-orphan")
    sound_effects = relationship("SoundEffect", back_populates="user", cascade="all, delete-orphan")
    scripts = relationship("Script", back_populates="user", cascade="all, delete-orphan")
    generation_history = relationship("GenerationHistory", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class Session(Base):
    """User session model for token management"""
    __tablename__ = "sessions"

    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(512), unique=True, nullable=False, index=True)

    # Session info
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(512), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_activity_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    metadata = Column(JSON, default=dict, nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")

    # Indexes
    __table_args__ = (
        Index("idx_session_user_active", "user_id", "is_active"),
        Index("idx_session_expires", "expires_at"),
    )

    def __repr__(self):
        return f"<Session(id={self.session_id}, user_id={self.user_id})>"


# ============================================================================
# Asset Models
# ============================================================================

class Sprite(Base):
    """Generated sprite asset model"""
    __tablename__ = "sprites"

    sprite_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Content
    description = Column(Text, nullable=False)
    file_path = Column(String(512), nullable=False)
    thumbnail_path = Column(String(512), nullable=True)

    # Sprite properties
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    format = Column(String(50), nullable=True)  # PNG, GIF, etc.

    # Generation metadata
    generation_id = Column(String(36), ForeignKey("generation_history.id"), nullable=True)
    style_preset = Column(String(100), nullable=True)
    prompt = Column(Text, nullable=True)
    negative_prompt = Column(Text, nullable=True)
    seed = Column(Integer, nullable=True)

    # Tags and categorization
    tags = Column(JSON, default=list, nullable=True)
    category = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Metadata
    metadata = Column(JSON, default=dict, nullable=True)

    # Relationships
    user = relationship("User", back_populates="sprites")
    generation = relationship("GenerationHistory", back_populates="sprites")

    # Indexes
    __table_args__ = (
        Index("idx_sprite_user_created", "user_id", "created_at"),
        Index("idx_sprite_category", "category"),
    )

    def __repr__(self):
        return f"<Sprite(id={self.sprite_id}, description={self.description[:30]})>"


class MusicTrack(Base):
    """Generated music track model"""
    __tablename__ = "music_tracks"

    track_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Content
    description = Column(Text, nullable=False)
    file_path = Column(String(512), nullable=False)

    # Track properties
    duration_seconds = Column(Float, nullable=True)
    format = Column(String(50), nullable=True)  # MOD, UGE, MIDI, etc.
    tempo = Column(Integer, nullable=True)
    key_signature = Column(String(10), nullable=True)

    # Generation metadata
    generation_id = Column(String(36), ForeignKey("generation_history.id"), nullable=True)
    style = Column(String(100), nullable=True)
    mood = Column(String(100), nullable=True)

    # Tags and categorization
    tags = Column(JSON, default=list, nullable=True)
    category = Column(String(100), nullable=True)  # battle, overworld, menu, etc.

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Metadata
    metadata = Column(JSON, default=dict, nullable=True)

    # Relationships
    user = relationship("User", back_populates="music_tracks")
    generation = relationship("GenerationHistory", back_populates="music_tracks")

    # Indexes
    __table_args__ = (
        Index("idx_music_user_created", "user_id", "created_at"),
        Index("idx_music_category", "category"),
    )

    def __repr__(self):
        return f"<MusicTrack(id={self.track_id}, description={self.description[:30]})>"


class SoundEffect(Base):
    """Generated sound effect model"""
    __tablename__ = "sound_effects"

    sfx_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Content
    description = Column(Text, nullable=False)
    file_path = Column(String(512), nullable=False)

    # SFX properties
    duration_seconds = Column(Float, nullable=True)
    format = Column(String(50), nullable=True)  # WAV, VGM, etc.
    sample_rate = Column(Integer, nullable=True)

    # Generation metadata
    generation_id = Column(String(36), ForeignKey("generation_history.id"), nullable=True)
    effect_type = Column(String(100), nullable=True)  # jump, coin, explosion, etc.

    # Tags and categorization
    tags = Column(JSON, default=list, nullable=True)
    category = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Metadata
    metadata = Column(JSON, default=dict, nullable=True)

    # Relationships
    user = relationship("User", back_populates="sound_effects")
    generation = relationship("GenerationHistory", back_populates="sound_effects")

    # Indexes
    __table_args__ = (
        Index("idx_sfx_user_created", "user_id", "created_at"),
        Index("idx_sfx_category", "category"),
    )

    def __repr__(self):
        return f"<SoundEffect(id={self.sfx_id}, description={self.description[:30]})>"


class Script(Base):
    """GB Studio script/event model"""
    __tablename__ = "scripts"

    script_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Content
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    events = Column(JSON, nullable=False)  # GB Studio event structure

    # Script properties
    script_type = Column(String(100), nullable=True)  # actor, trigger, scene, etc.
    complexity_score = Column(Integer, nullable=True)

    # Generation metadata
    generation_id = Column(String(36), ForeignKey("generation_history.id"), nullable=True)

    # Tags and categorization
    tags = Column(JSON, default=list, nullable=True)
    category = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Metadata
    metadata = Column(JSON, default=dict, nullable=True)

    # Relationships
    user = relationship("User", back_populates="scripts")
    generation = relationship("GenerationHistory", back_populates="scripts")

    # Indexes
    __table_args__ = (
        Index("idx_script_user_created", "user_id", "created_at"),
        Index("idx_script_type", "script_type"),
    )

    def __repr__(self):
        return f"<Script(id={self.script_id}, name={self.name})>"


# ============================================================================
# System Models
# ============================================================================

class GenerationHistory(Base):
    """Asset generation history and tracking"""
    __tablename__ = "generation_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Generation details
    asset_type = Column(SQLEnum(AssetType), nullable=False)
    status = Column(SQLEnum(GenerationStatus), default=GenerationStatus.PENDING, nullable=False)

    # Input/Output
    input_prompt = Column(Text, nullable=False)
    input_parameters = Column(JSON, default=dict, nullable=True)
    output_path = Column(String(512), nullable=True)
    output_metadata = Column(JSON, default=dict, nullable=True)

    # Performance metrics
    duration_seconds = Column(Float, nullable=True)
    cost_credits = Column(Float, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Metadata
    metadata = Column(JSON, default=dict, nullable=True)

    # Relationships
    user = relationship("User", back_populates="generation_history")
    sprites = relationship("Sprite", back_populates="generation")
    music_tracks = relationship("MusicTrack", back_populates="generation")
    sound_effects = relationship("SoundEffect", back_populates="generation")
    scripts = relationship("Script", back_populates="generation")

    # Indexes
    __table_args__ = (
        Index("idx_generation_user_created", "user_id", "created_at"),
        Index("idx_generation_status", "status"),
        Index("idx_generation_type", "asset_type"),
    )

    def __repr__(self):
        return f"<GenerationHistory(id={self.id}, type={self.asset_type}, status={self.status})>"


class AuditLog(Base):
    """System audit log for tracking user actions"""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Action details
    action = Column(String(255), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(36), nullable=True)

    # Request details
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    endpoint = Column(String(512), nullable=True)
    method = Column(String(10), nullable=True)  # GET, POST, etc.

    # Result
    status_code = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Details
    details = Column(JSON, default=dict, nullable=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    # Indexes
    __table_args__ = (
        Index("idx_audit_user_timestamp", "user_id", "timestamp"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, timestamp={self.timestamp})>"
