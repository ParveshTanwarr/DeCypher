# Recovering Neo4j credentials without deleting graph data

Neo4j applies `NEO4J_AUTH` when its data directory is initialized for the first time. If
`backend/.env` is later recreated from `.env.example` or its password is changed, the
existing `neo4jdata` volume keeps the old Neo4j user password. The healthcheck then reports
`The client is unauthorized due to authentication failure`.

**Do not run `docker compose down -v` or delete `neo4jdata`.** The volume contains the graph.

## Normal startup behavior

The API and Celery services depend on Neo4j being started, not on its authenticated healthcheck
being green. Neo4j is an optional graph projection and the API has a PostgreSQL graph fallback,
so a stale Neo4j password should not prevent the rest of the local application from starting.
The Neo4j healthcheck still validates the configured password and reports an authentication
mismatch accurately.

## Reset the existing Neo4j password

Run all commands from the `backend/` directory.

1. Stop Neo4j:

   ```bash
   docker compose stop neo4j
   ```

2. (Recommended) Back up the named volume before recovery:

   ```bash
   mkdir -p backups
   docker run --rm \
     -v backend_neo4jdata:/data:ro \
     -v "$PWD/backups":/backup \
     alpine sh -c 'tar -czf /backup/neo4jdata-before-auth-recovery.tar.gz -C /data .'
   ```

   If your Compose project uses a different volume name, find it with
   `docker volume ls` and replace `backend_neo4jdata` accordingly. Confirm the archive exists
   before continuing:

   ```bash
   ls -lh backups/neo4jdata-before-auth-recovery.tar.gz
   ```

3. Start Neo4j in temporary recovery mode. This overlay disables authentication only for this
   recovery container and disables the password-based healthcheck. The base Compose file binds
   Neo4j ports to localhost only.

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.neo4j-recovery.yml up -d neo4j
   docker compose logs -f neo4j
   ```

   Wait until the logs report that Neo4j has started. Then open a second terminal in
   `backend/` and connect to the local system database without credentials:

   ```bash
   docker exec -it threat_neo4j cypher-shell -d system
   ```

4. At the Cypher Shell prompt, set a new strong password (at least 8 characters):

   ```cypher
   ALTER USER neo4j SET PASSWORD 'REPLACE_WITH_A_NEW_STRONG_PASSWORD';
   ```

   Then exit with `:exit`. Use a password that does not contain a single quote for this
   interactive command, or escape quotes according to Cypher string-literal rules.

5. Stop the temporary recovery container and restart Neo4j with normal authentication:

   ```bash
   docker compose stop neo4j
   ```

   Update `NEO4J_PASSWORD` in `backend/.env` to exactly the new password you set above, then:

   ```bash
   docker compose up -d neo4j
   docker compose ps neo4j
   docker compose logs neo4j --tail=80
   ```

6. Verify authentication and then start the complete stack:

   ```bash
   docker exec threat_neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "RETURN 1 AS connected;"
   docker compose up -d
   curl http://127.0.0.1:8000/health
   ```

   Note: `docker exec` does not automatically read the host `.env` file. For the direct
   authentication test, either substitute the password locally in the command (do not paste it
   into chat) or use the healthcheck status from `docker compose ps`.

7. Once recovery is complete, do not use the recovery overlay again. Normal operation uses
   `docker-compose.yml` only.

## New installations and existing installations

- **New volume:** `NEO4J_AUTH` initializes the `neo4j` password from `NEO4J_PASSWORD`.
- **Existing volume:** changing `NEO4J_PASSWORD` does not change the stored database password.
  Use the recovery procedure above if the previous password is lost.
- Keep `NEO4J_PASSWORD` consistent between `backend/.env` and the persistent Neo4j database.

This procedure follows Neo4j's documented password recovery flow: disable authentication,
restrict access to localhost, run `ALTER USER` against the `system` database, then restore
authentication. See the [Neo4j Operations Manual: Recover admin user and password](https://neo4j.com/docs/operations-manual/current/authentication-authorization/password-and-user-recovery/).
