from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON, UniqueConstraint
from app.database.postgres import Base

def utc_now():
    return datetime.now(timezone.utc)

class EvidenceLedgerBlock(Base):
    __tablename__ = "evidence_ledger_blocks"
    id = Column(Integer, primary_key=True, index=True)
    block_index = Column(Integer, unique=True, index=True, nullable=False)
    first_sequence_id = Column(Integer, nullable=False)
    last_sequence_id = Column(Integer, nullable=False)
    previous_block_hash = Column(String(64), nullable=False)
    merkle_root = Column(String(64), nullable=False)
    block_hash = Column(String(64), unique=True, nullable=False, index=True)
    entry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

class CollectionSource(Base):
    __tablename__ = "collection_sources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, nullable=False)
    kind = Column(String(32), nullable=False)
    url = Column(String(1024), nullable=False)
    actor_id = Column(String(64), ForeignKey("actors.actor_id", ondelete="SET NULL"), index=True, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    interval_minutes = Column(Integer, default=15, nullable=False)
    headers = Column(JSON, nullable=False, default=dict)
    parser_config = Column(JSON, nullable=False, default=dict)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    last_status = Column(String(32), default="never", nullable=False)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

class CollectionRun(Base):
    __tablename__ = "collection_runs"
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("collection_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=utc_now)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), default="running", nullable=False)
    items_seen = Column(Integer, default=0, nullable=False)
    observations_created = Column(Integer, default=0, nullable=False)
    entities_created = Column(Integer, default=0, nullable=False)
    error = Column(Text, nullable=True)

class ExternalEntity(Base):
    __tablename__ = "external_entities"
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(32), nullable=False, index=True)
    canonical_value = Column(String(512), nullable=False, index=True)
    display_name = Column(String(512), nullable=True)
    source = Column(String(128), nullable=False)
    confidence = Column(Float, default=0.5, nullable=False)
    entity_metadata = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    __table_args__ = (UniqueConstraint("entity_type", "canonical_value", "source", name="uq_external_entity"),)

class EntityLink(Base):
    __tablename__ = "entity_links"
    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(String(64), ForeignKey("actors.actor_id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id = Column(Integer, ForeignKey("external_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    match_type = Column(String(64), nullable=False)
    explanation = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    __table_args__ = (UniqueConstraint("actor_id", "entity_id", name="uq_entity_link_actor_entity"),)

class MediaEvidence(Base):
    __tablename__ = "media_evidence"
    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(String(64), ForeignKey("actors.actor_id", ondelete="SET NULL"), nullable=True, index=True)
    media_id = Column(String(128), unique=True, nullable=False, index=True)
    source = Column(String(128), nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    phash = Column(String(32), nullable=False, index=True)
    mime_type = Column(String(128), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

class StylometryDiscovery(Base):
    __tablename__ = "stylometry_discoveries"
    id = Column(Integer, primary_key=True, index=True)
    handle_a = Column(String(128), nullable=False, index=True)
    handle_b = Column(String(128), nullable=False, index=True)
    actor_a = Column(String(64), nullable=True, index=True)
    actor_b = Column(String(64), nullable=True, index=True)
    similarity = Column(Float, nullable=False)
    same_author = Column(Boolean, nullable=False, default=False)
    model_status = Column(String(64), nullable=False)
    evidence = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(String(64), ForeignKey("actors.actor_id", ondelete="SET NULL"), nullable=True, index=True)
    alert_type = Column(String(64), nullable=False, index=True)
    severity = Column(String(16), nullable=False, default="medium")
    title = Column(String(256), nullable=False)
    message = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    id = Column(Integer, primary_key=True, index=True)
    evaluation_type = Column(String(64), nullable=False, index=True)
    source = Column(String(256), nullable=False)
    status = Column(String(32), nullable=False, default="completed")
    metrics = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
