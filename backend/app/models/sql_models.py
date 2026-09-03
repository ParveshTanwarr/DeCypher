from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, UniqueConstraint
from datetime import datetime
from app.database.postgres import Base

class DarkWebHandle(Base):
    __tablename__ = "darkweb_handles"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(String(64), index=True, nullable=True)
    handle = Column(String(128), index=True, nullable=False)
    platform = Column(String(64), nullable=True)
    status = Column(String(32), default="active")
    registration_date = Column(DateTime, nullable=True)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    stylometry_vector_hash = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("handle", "platform", name="uq_handle_platform"),
    )

class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(String(64), index=True, nullable=True)
    address = Column(String(256), unique=True, index=True, nullable=False)
    currency = Column(String(16), default="BTC")
    associated_handle = Column(String(128), index=True, nullable=True)
    first_seen = Column(DateTime, default=datetime.utcnow)

class Marketplace(Base):
    __tablename__ = "marketplaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, index=True, nullable=False)
    onion_url = Column(String(256), unique=True, nullable=True)
    status = Column(String(32), default="active")

class InvestigatorFeedback(Base):
    __tablename__ = "investigator_feedback"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(String(64), index=True, nullable=False)
    decision = Column(String(32), nullable=False)
    notes = Column(Text, nullable=True)
    investigator_name = Column(String(128), default="analyst")
    timestamp = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(128), index=True, nullable=False)
    method = Column(String(16), nullable=False)
    endpoint = Column(String(256), nullable=False)
    query_params = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    observation_id = Column(String, unique=True, index=True, nullable=False)
    indicator_type = Column(String, index=True, nullable=False)
    detected = Column(Boolean, default=True)
    value = Column(String, nullable=False)
    target = Column(String, index=True, nullable=False)
    source = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    confidence = Column(Float, default=1.0)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Actor(Base):
    __tablename__ = "actors"

    actor_id = Column(String(64), primary_key=True, index=True)
    primary_handle = Column(String(128), nullable=False)
    risk_category = Column(String(32), default="High")
    confidence_score = Column(Float, default=0.85)
    priority_score = Column(Integer, default=70)
    created_at = Column(DateTime, default=datetime.utcnow)