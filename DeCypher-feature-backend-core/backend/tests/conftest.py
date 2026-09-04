"""
Shared pytest fixtures.

Runs against the real Postgres pointed to by DATABASE_URL (see
app/config.py / .env) -- there was no test suite before this, and the
ON CONFLICT upserts in ingestion.py are Postgres-specific, so a
SQLite-backed in-memory DB won't work here. Point DATABASE_URL at a
disposable database before running pytest (e.g. `docker-compose up -d
postgres`) -- the session fixture below drops and recreates every table.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def _seed_database():
    from app.services.ingestion import init_db_and_load_csvs
    # sync_neo4j=False: tests shouldn't require a running Neo4j instance.
    # graph_service has its own unit tests with a mocked driver instead.
    init_db_and_load_csvs(reset_tables=True, sync_neo4j=False)
    yield


@pytest.fixture(scope="session")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_token(client):
    r = client.post("/auth/token", data={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def analyst_token(client):
    r = client.post("/auth/token", data={"username": "analyst", "password": "analystpassword"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def analyst_headers(analyst_token):
    return {"Authorization": f"Bearer {analyst_token}"}
