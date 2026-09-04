"""
Regression tests for the ingestion pipeline. This covers the bugs found
during review: wrong DATA_DIR path, actors.csv/handles.csv column
mismatches causing NOT NULL failures, and wallets never getting an
actor_id because wallets.csv only has handle_id.
"""
from sqlalchemy import func
from app.database.postgres import SessionLocal
from app.models.sql_models import Actor, DarkWebHandle, Wallet, Marketplace, Observation


def test_actors_loaded_with_primary_handle():
    db = SessionLocal()
    try:
        total = db.query(func.count(Actor.actor_id)).scalar()
        assert total > 0, "actors table is empty -- ingestion did not run"

        missing_primary_handle = db.query(Actor).filter(Actor.primary_handle.is_(None)).count()
        assert missing_primary_handle == 0, "every actor should have a derived primary_handle"
    finally:
        db.close()


def test_handles_linked_to_actors():
    db = SessionLocal()
    try:
        total = db.query(func.count(DarkWebHandle.id)).scalar()
        assert total > 0

        missing_actor_id = db.query(DarkWebHandle).filter(DarkWebHandle.actor_id.is_(None)).count()
        assert missing_actor_id == 0, "every ingested handle should be linked to an actor"
    finally:
        db.close()


def test_wallets_linked_to_actors_and_handles():
    """
    wallets.csv only has handle_id, not actor_id -- without the join
    through handles.csv, every wallet's actor_id/associated_handle would
    be NULL, silently dropping the wallet-reuse correlation signal.
    """
    db = SessionLocal()
    try:
        total = db.query(func.count(Wallet.address)).scalar()
        assert total > 0

        missing_actor_id = db.query(Wallet).filter(Wallet.actor_id.is_(None)).count()
        missing_handle = db.query(Wallet).filter(Wallet.associated_handle.is_(None)).count()
        assert missing_actor_id == 0, "wallets should be linked to an actor via handles.csv"
        assert missing_handle == 0, "wallets should be linked to the handle that used them"
    finally:
        db.close()


def test_known_actor_has_multiple_correlated_handles():
    """Ground-truth spot check: A00001 has two handles that share a wallet."""
    db = SessionLocal()
    try:
        handles = {h.handle for h in db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == "A00001").all()}
        assert {"nyxinhex99", "vexatrace"}.issubset(handles)
    finally:
        db.close()


def test_marketplaces_loaded():
    db = SessionLocal()
    try:
        assert db.query(func.count(Marketplace.name)).scalar() > 0
    finally:
        db.close()


def test_infrastructure_observations_loaded():
    """
    data/infrastructure_indicators.csv previously wasn't ingested anywhere,
    so GET /actors/{id}/evidence always returned an empty list.
    """
    db = SessionLocal()
    try:
        assert db.query(func.count(Observation.observation_id)).scalar() > 0
    finally:
        db.close()


def test_ingestion_is_idempotent():
    """Re-running ingestion without reset_tables should not error or duplicate rows."""
    from app.services.ingestion import init_db_and_load_csvs

    db = SessionLocal()
    try:
        before = db.query(func.count(Actor.actor_id)).scalar()
    finally:
        db.close()

    init_db_and_load_csvs(reset_tables=False, sync_neo4j=False)

    db = SessionLocal()
    try:
        after = db.query(func.count(Actor.actor_id)).scalar()
    finally:
        db.close()

    assert before == after
