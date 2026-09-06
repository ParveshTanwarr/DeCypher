from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship
from app.database.postgres import Base


def utc_now():
    return datetime.now(timezone.utc)


class Actor(Base):
    __tablename__ = "actors"

    actor_id = Column(String(64), primary_key=True, index=True)
    primary_handle = Column(String(128), nullable=False)
    risk_category = Column(String(32), default="High")
    confidence_score = Column(Float, default=0.85)
    priority_score = Column(Integer, default=70)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now())

    # Relationships
    handles = relationship("DarkWebHandle", back_populates="actor", cascade="all, delete-orphan")
    wallets = relationship("Wallet", back_populates="actor", cascade="all, delete-orphan")
    feedback = relationship("InvestigatorFeedback", back_populates="actor", cascade="all, delete-orphan")


class DarkWebHandle(Base):
    __tablename__ = "darkweb_handles"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(String(64), ForeignKey("actors.actor_id", ondelete="CASCADE"), index=True, nullable=True)
    handle = Column(String(128), index=True, nullable=False)
    platform = Column(String(64), nullable=True)
    status = Column(String(32), default="active")
    registration_date = Column(DateTime(timezone=True), nullable=True)
    first_seen = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    stylometry_vector_hash = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now())

    actor = relationship("Actor", back_populates="handles")

    __table_args__ = (
        UniqueConstraint("handle", "platform", name="uq_handle_platform"),
    )


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(String(64), ForeignKey("actors.actor_id", ondelete="CASCADE"), index=True, nullable=True)
    address = Column(String(256), unique=True, index=True, nullable=False)
    currency = Column(String(16), default="BTC")
    associated_handle = Column(String(128), index=True, nullable=True)
    first_seen = Column(DateTime(timezone=True), default=utc_now)

    actor = relationship("Actor", back_populates="wallets")


class Marketplace(Base):
    __tablename__ = "marketplaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, index=True, nullable=False)
    onion_url = Column(String(256), unique=True, nullable=True)
    status = Column(String(32), default="active")


class InvestigatorFeedback(Base):
    __tablename__ = "investigator_feedback"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(String(64), ForeignKey("actors.actor_id", ondelete="CASCADE"), index=True, nullable=False)
    verdict = Column(String(32), nullable=False)  # Renamed from 'decision' to match API & schemas
    notes = Column(Text, nullable=True)
    investigator_id = Column(String(128), default="analyst")  # Renamed from 'investigator_name'
    timestamp = Column(DateTime(timezone=True), default=utc_now, server_default=func.now())

    actor = relationship("Actor", back_populates="feedback")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(128), index=True, nullable=False)
    method = Column(String(16), nullable=False)
    endpoint = Column(String(256), nullable=False)
    query_params = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utc_now, server_default=func.now())


class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    observation_id = Column(String(128), unique=True, index=True, nullable=False)
    indicator_type = Column(String(64), index=True, nullable=False)
    detected = Column(Boolean, default=True)
    value = Column(String(512), nullable=True)
    target = Column(String(256), index=True, nullable=False)
    source = Column(String(128), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utc_now)
    confidence = Column(Float, default=1.0)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now())