from sqlalchemy import Column, String, Integer, DateTime, Text
from datetime import datetime
from app.database.postgres import Base

class Handle(Base):
    __tablename__ = "handles"
    handle_id = Column(String, primary_key=True, index=True)
    handle_name = Column(String, index=True)
    platform = Column(String)
    first_seen = Column(String)
    last_seen = Column(String)

class Wallet(Base):
    __tablename__ = "wallets"
    wallet_address = Column(String, primary_key=True, index=True)
    currency = Column(String)
    handle_id = Column(String, index=True)

class Marketplace(Base):
    __tablename__ = "marketplaces"
    marketplace_id = Column(String, primary_key=True, index=True)
    name = Column(String)
    onion_url = Column(String)
    status = Column(String)

class InvestigatorFeedback(Base):
    __tablename__ = "investigator_feedback"
    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(String, index=True)
    verdict = Column(String)
    investigator_id = Column(String)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, index=True)
    method = Column(String)
    endpoint = Column(String)
    query_params = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)