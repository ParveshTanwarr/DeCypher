# Advanced Intelligence

This feature layer closes the repository gaps identified during the October 2026 audit.

## Evidence integrity

The original SHA-256 observation chain remains authoritative. EvidenceLedgerBlock adds Merkle-rooted blocks over ledger records, with chained block hashes. The API exposes GET /integrity/merkle-status, GET /integrity/merkle-verify, and POST /integrity/merkle-seal (admin). Set LEDGER_BLOCK_SIZE to control block size. The current repository does not ship a public-chain transaction signer; optional external anchoring is a deployment boundary controlled by BLOCKCHAIN_ANCHOR_RPC_URL and BLOCKCHAIN_ANCHOR_CONTRACT.

## Continuous multi-source collection

Collection sources support rss, json, html, and tor_http connectors. Each source is explicitly registered, allowlisted, persisted, and polled by Celery Beat + Redis when COLLECTION_ENABLED=true.

Relevant endpoints: POST /collection/sources, GET /collection/sources, POST /collection/sources/{source_id}/run, GET /collection/runs, GET /collection/status.

Hosts must be present in COLLECTION_ALLOWED_HOSTS, a source-level parser_config.allowed_hosts list, or the Tor allowlist for .onion targets.

## Tor intelligence

POST /tor/inspect performs an allowlisted hidden-service observation through TOR_SOCKS5_PROXY. POST /tor/descriptor/parse parses supplied relay descriptor text into normalized fields.

The bundled project intentionally does not include arbitrary public .onion targets. Add only explicitly authorized or otherwise appropriate intelligence sources to TOR_ALLOWED_ONION_HOSTS.

## Automatic stylometry discovery

POST /correlation/stylometry-discovery samples candidate handle pairs, routes them through the same bundled authorship engine used by normal correlation, and stores discovery results. The process is capped to avoid quadratic scans over the full handle population.

## Interactive evidence ablation

POST /correlation/actor/{actor_id}/ablation disables selected evidence signals and recomputes the current evidence-fusion score. This is sensitivity analysis, not a causal effect or identity proof.

## Calibration and historical evaluation

GET /evaluation/calibration computes Brier score, ECE and reliability bins for stylometry similarity against synthetic actor labels.

POST /evaluation/historical-cases evaluates a documented case manifest supplied by the investigator. The repository provides the harness and provenance fields; public case data must be supplied under an appropriate license and provenance record.

## Cross-modal image correlation

POST /media/fingerprint stores SHA-256 plus a perceptual dHash for an investigator-supplied image.

POST /media/compare compares two stored images using perceptual Hamming distance and exact SHA-256 equality.

Perceptual similarity is treated as a reuse/near-duplicate signal, not ownership proof.

## Real-world technical entity linkage

Collection extracts technical entities such as handles, wallets, PGP fingerprints and .onion domains. EntityLinkageService links these against an actor's recorded technical identities and allowlisted infrastructure targets using explicit match types.

## Live alerts

/alerts/ws is a WebSocket endpoint. The client authenticates by sending its bearer JWT as the first WebSocket message. New persisted collection/Tor alerts are then streamed to the investigator UI.

## Advanced graph anomaly analysis

The structural anomaly population now includes two-hop trust reach and temporal event density in addition to wallet/PGP/infrastructure reuse, marketplace switching, lifecycle overlap and source diversity.
