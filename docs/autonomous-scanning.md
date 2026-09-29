# Autonomous Scanning

DeCypher's autonomous scanning layer is implemented with Celery + Redis and is intentionally
disabled by default.

## Architecture

```
Celery Beat (1 minute)
        |
        v
due ScanTarget records
        |
        v
Redis queue
        |
        v
Celery worker
        |
        v
authorized infra scanner
        |
        +----> PostgreSQL observations
        |
        +----> Neo4j observation sync
        |
        +----> correlation + priority recalculation
        |
        v
next_run_at updated
```

## Safety model

Autonomous targets are accepted only when their hostname is explicitly listed in
`AUTOSCAN_ALLOWED_HOSTS`. The repository default is loopback-only:

```text
127.0.0.1,localhost
```

Do not add public or third-party targets to the allowlist. Use only infrastructure
you own or have explicit authorization to test.

## Local setup

From `backend/`:

```powershell
pip install -r requirements.txt
docker compose up -d
```

Enable the feature in `.env`:

```text
AUTOSCAN_ENABLED=true
AUTOSCAN_DEFAULT_INTERVAL_MINUTES=180
AUTOSCAN_ALLOWED_HOSTS=127.0.0.1,localhost
```

Start the API:

```powershell
uvicorn app.main:app --reload --port 8000
```

Start a Celery worker in another terminal on Windows:

```powershell
celery -A app.workers.celery_app.celery_app worker --loglevel=info --pool=solo
```

Start Celery Beat in a third terminal:

```powershell
celery -A app.workers.celery_app.celery_app beat --loglevel=info
```

Beat dispatches due targets once per minute. The target's own interval controls when it becomes due.

## API workflow

Create an authorized target as an admin/service account:

```http
POST /scanner/targets
```

Example:

```json
{
  "name": "local-demo-service",
  "target_url": "http://127.0.0.1:9000/",
  "actor_id": "A00358",
  "interval_minutes": 180,
  "priority_aware": true,
  "enabled": true
}
```

Queue it immediately:

```http
POST /scanner/targets/1/run
```

Inspect:

```http
GET /scanner/jobs
GET /scanner/jobs/1
GET /scanner/targets
```

The worker stores scan findings, attempts a Neo4j evidence sync, recalculates the actor's
correlation/priority score, and schedules the next scan.

## Priority-aware rescanning

When enabled for a target:

- priority >= 85 -> 15-minute interval
- priority >= 70 -> 30-minute interval
- priority >= 50 -> 60-minute interval
- lower priority -> configured interval

The interval has a five-minute minimum. Failed scans retry after five minutes.

This is an operational scheduling policy, not an identity-probability model.
