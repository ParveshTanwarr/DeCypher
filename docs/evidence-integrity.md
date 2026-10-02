# Evidence Integrity Ledger

DeCypher maintains an append-only, tamper-evident hash chain for structured observation evidence.

## What is recorded

Each ingested observation can produce one ledger entry containing its observation identifier, optional actor identifier, event type, canonical evidence payload, creation timestamp and producer identity, previous record hash, and current record hash.

The current prototype stores the chain in PostgreSQL. It is an **internal hash chain**, not a blockchain network. The API explicitly reports whether an external blockchain anchor is configured; the bundled implementation does not claim external anchoring.

## Hash construction

The record hash is SHA-256 over a canonical JSON representation of the database sequence identifier, previous record hash, event type, observation identifier, actor identifier, producer identity, creation timestamp, and normalized evidence payload. A fixed genesis hash initializes the chain.

## Concurrency and integrity

PostgreSQL advisory locking serializes ledger appends so concurrent ingestion requests cannot observe the same chain head and fork the hash sequence.

Observation ingestion and ledger insertion occur in the same database transaction. If the integrity entry cannot be written, the observation transaction is rolled back.

Startup backfills missing ledger records for observations already present in PostgreSQL, allowing existing demo data to become covered without duplicating entries.

## API

All integrity endpoints require authentication.

- `GET /integrity/status` — chain mode, entry count and current head hash.
- `GET /integrity/verify` — recomputes the complete chain and reports the first broken link or record hash.
- `GET /integrity/ledger?limit=25&actor_id=A00001` — retrieve recent ledger entries, optionally scoped to an actor.

## Interpretation

A valid hash chain demonstrates consistency of the records stored in the ledger relative to the canonical hashing rules. It does **not** by itself prove that the underlying observation was truthful, independently sourced, or produced by a particular actor.

An external blockchain anchor can be added later by periodically publishing a trusted ledger-head hash to a configured external system. That capability is not enabled in the current repository.
