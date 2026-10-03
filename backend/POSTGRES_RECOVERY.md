# Recovering PostgreSQL credentials without deleting database data

The Compose PostgreSQL service uses the persistent named volume `pgdata`. On an existing
volume, the official PostgreSQL image does **not** reapply `POSTGRES_PASSWORD` from
`backend/.env`. That variable initializes a new database directory only. If the API reports
`password authentication failed for user "postgres"`, the password stored by PostgreSQL and
the value used to build `DATABASE_URL` have drifted.

**Do not run `docker compose down -v`, remove `pgdata`, or recreate the database volume.**

## Port mapping

The local development stack publishes PostgreSQL as `127.0.0.1:5433:5432`. This avoids
collisions with a PostgreSQL server installed on the Mac at `127.0.0.1:5432`.
Containers still connect to `postgres:5432` on the Compose network. When running FastAPI
directly on the host, `DATABASE_URL` in `.env` must use port `5433`.

## Diagnose the exact network path

Run from `backend/`:

```bash
docker compose exec postgres sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" psql -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -Atqc "SELECT 1"'
```

This deliberately connects through the Compose service hostname `postgres`, rather than
loopback. It tests the same network route and password authentication used by the API.
A successful `127.0.0.1` test inside the database container alone does not prove that
Docker-network connections use the same `pg_hba.conf` rule.

- If it prints `1`, the configured password is accepted over the Compose network. If the API
  still fails, inspect the API's effective URL/driver configuration and PostgreSQL logs.
- If it reports password authentication failure while a loopback test succeeds, inspect
  `pg_hba.conf` and PostgreSQL logs; local and Docker-network connections may match different
  authentication rules.

The Compose PostgreSQL healthcheck now runs this authenticated query over the service
hostname. Unlike `pg_isready`, it validates the credentials used by the application.

## Align the existing PostgreSQL password

Run commands from `backend/`.

1. Confirm the container is running:

   ```bash
   docker compose ps postgres
   ```

2. (Recommended) Make a cold copy of the data volume before changing credentials. Find the
   actual volume name and mount point:

   ```bash
   docker inspect threat_postgres --format '{{range .Mounts}}{{println .Name "->" .Destination}}{{end}}'
   ```

   Stop PostgreSQL, then substitute the volume name shown above if it is not
   `backend_pgdata`:

   ```bash
   docker compose stop postgres
   mkdir -p backups
   docker run --rm \
     -v backend_pgdata:/var/lib/postgresql/data:ro \
     -v "$PWD/backups":/backup \
     alpine sh -c 'tar -czf /backup/postgres-before-password-recovery.tar.gz -C /var/lib/postgresql/data .'
   ls -lh backups/postgres-before-password-recovery.tar.gz
   docker compose up -d postgres
   ```

   Do not proceed until the archive exists and PostgreSQL is healthy again:

   ```bash
   docker compose ps postgres
   ```

3. Open a local administrative shell inside the PostgreSQL container. This uses the container's
   local Unix socket; it does not connect over the Mac's occupied host port:

   ```bash
   docker exec -it threat_postgres psql -U postgres -d postgres
   ```

4. At the `psql` prompt, use PostgreSQL's interactive password command:

   ```sql
   \password postgres
   ```

   Enter a new strong password twice. The password is not echoed and does not need to appear
   in shell history. Exit with `\q`.

5. Set **the same password** as `POSTGRES_PASSWORD` in `backend/.env`. Keep the host-side
   `DATABASE_URL` password in sync too if you run FastAPI outside Docker. Do not paste
   credentials into chat or commit `.env`.

6. Recreate only the application containers so Compose interpolates the updated password
   into `DATABASE_URL`. The PostgreSQL data volume is left intact:

   ```bash
   docker compose up -d --force-recreate api celery_worker celery_beat
   docker compose ps
   docker compose logs --tail=100 api
   curl http://127.0.0.1:8000/health
   ```

   The PostgreSQL healthcheck now verifies password authentication over the Docker network.
   Confirm the API logs no longer contain an authentication failure.

## If local administrative access fails

Do not delete or initialize the volume again. Stop here and inspect the exact `psql` error
and PostgreSQL logs before attempting another recovery method.
