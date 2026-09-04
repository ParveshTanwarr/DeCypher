# Backend tests

Run against a real Postgres (the ON CONFLICT upserts in `ingestion.py`
are Postgres-specific, so SQLite won't work here). Point `DATABASE_URL`
at a **disposable** database first -- the test session fixture drops and
recreates every table on startup.

```bash
# from the backend/ directory, with the docker-compose postgres up:
docker-compose up -d postgres
pytest
```

Neo4j is not required to run these -- `graph_service.py` has its own
unit tests using a mocked driver, and the live `/actors/{id}/graph`
test only checks that it falls back gracefully when Neo4j isn't there.
