from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from io import BytesIO
from typing import Any, Iterable
from urllib.parse import urlparse

import requests
from PIL import Image
from sqlalchemy import func

from app.config import settings
from app.models.advanced_models import (
    Alert,
    CollectionRun,
    CollectionSource,
    EntityLink,
    EvaluationRun,
    EvidenceLedgerBlock,
    ExternalEntity,
    MediaEvidence,
    StylometryDiscovery,
)
from app.models.sql_models import Actor, DarkWebHandle, Observation
from app.services.nlp_service import nlp_service
from app.services.evidence_ledger import EvidenceLedgerService


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _sha256(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _normal(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def image_perceptual_hash(data: bytes) -> tuple[str, int, int, str]:
    with Image.open(BytesIO(data)) as original:
        mime = Image.MIME.get(original.format or "", "image/*")
        image = original.convert("L")
        width, height = image.size
        resized = image.resize((9, 8))
        pixels = list(resized.getdata())

    bits = []
    for row in range(8):
        for col in range(8):
            left = pixels[row * 9 + col]
            right = pixels[row * 9 + col + 1]
            bits.append("1" if left > right else "0")
    bit_string = "".join(bits)
    phash = f"{int(bit_string, 2):016x}"
    return phash, width, height, mime


def phash_distance(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


def _read_limited_response(response: requests.Response, max_bytes: int) -> bytes:
    """Read an HTTP response without allowing unbounded response buffering."""
    limit = max(1, int(max_bytes))
    declared = response.headers.get("content-length")
    if declared:
        try:
            declared_length = int(declared)
        except ValueError:
            declared_length = None
        if declared_length is not None and declared_length > limit:
            raise ValueError(f"Response exceeds configured {limit}-byte limit.")

    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > limit:
            raise ValueError(f"Response exceeds configured {limit}-byte limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def _merkle_root(hashes: list[str]) -> str:
    if not hashes:
        return _sha256(b"DECYPHER-EMPTY-MERKLE")
    level = [h for h in hashes]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            right = level[i + 1] if i + 1 < len(level) else level[i]
            nxt.append(_sha256(level[i] + right))
        level = nxt
    return level[0]


class MerkleEvidenceService:
    def __init__(self, db):
        self.db = db

    def seal_pending(self) -> int:
        from app.models.sql_models import EvidenceLedgerEntry

        EvidenceLedgerService(self.db)._lock_chain()

        all_entries = (
            self.db.query(EvidenceLedgerEntry)
            .order_by(EvidenceLedgerEntry.id.asc())
            .all()
        )
        block_size = max(1, int(settings.LEDGER_BLOCK_SIZE))
        existing_last = (
            self.db.query(EvidenceLedgerBlock)
            .order_by(EvidenceLedgerBlock.block_index.desc())
            .first()
        )
        next_index = (existing_last.block_index + 1) if existing_last else 0
        previous_block_hash = existing_last.block_hash if existing_last else _sha256(
            b"DECYPHER-EVIDENCE-BLOCK-GENESIS-v1"
        )
        sealed_until = existing_last.last_sequence_id if existing_last else 0

        # Sequence IDs are database primary keys and may contain gaps after
        # deletes/repairs. Never use the numeric ID as an array offset.
        pending_entries = [entry for entry in all_entries if entry.id > sealed_until]
        created = 0

        for offset in range(0, len(pending_entries), block_size):
            chunk = pending_entries[offset:offset + block_size]
            root = _merkle_root([entry.record_hash for entry in chunk])
            block_payload = {
                "block_index": next_index,
                "first_sequence_id": chunk[0].id,
                "last_sequence_id": chunk[-1].id,
                "previous_block_hash": previous_block_hash,
                "merkle_root": root,
                "entry_count": len(chunk),
            }
            block_hash = _sha256(
                json.dumps(block_payload, sort_keys=True, separators=(",", ":"))
            )
            self.db.add(EvidenceLedgerBlock(
                block_index=next_index,
                first_sequence_id=chunk[0].id,
                last_sequence_id=chunk[-1].id,
                previous_block_hash=previous_block_hash,
                merkle_root=root,
                block_hash=block_hash,
                entry_count=len(chunk),
            ))
            created += 1
            previous_block_hash = block_hash
            next_index += 1

        return created

    def verify(self) -> dict[str, Any]:
        from app.models.sql_models import EvidenceLedgerEntry
        blocks = self.db.query(EvidenceLedgerBlock).order_by(EvidenceLedgerBlock.block_index.asc()).all()
        entries = self.db.query(EvidenceLedgerEntry).order_by(EvidenceLedgerEntry.id.asc()).all()
        previous_hash = _sha256(b"DECYPHER-EVIDENCE-BLOCK-GENESIS-v1")
        covered_entry_ids: set[int] = set()
        previous_last_sequence = 0

        for index, block in enumerate(blocks):
            if block.block_index != index:
                return {"valid": False, "reason": f"Unexpected block index {block.block_index}; expected {index}.", "block_index": block.block_index}
            if block.first_sequence_id > block.last_sequence_id:
                return {"valid": False, "reason": f"Invalid sequence range in block {block.block_index}.", "block_index": block.block_index}
            if block.first_sequence_id <= previous_last_sequence:
                return {"valid": False, "reason": f"Overlapping block sequence range at block {block.block_index}.", "block_index": block.block_index}

            chunk = [
                e for e in entries
                if block.first_sequence_id <= e.id <= block.last_sequence_id
            ]
            if len(chunk) != block.entry_count:
                return {"valid": False, "reason": f"Block {block.block_index} entry count mismatch.", "block_index": block.block_index}
            if len({entry.id for entry in chunk}) != len(chunk):
                return {"valid": False, "reason": f"Duplicate ledger entry coverage in block {block.block_index}.", "block_index": block.block_index}

            root = _merkle_root([e.record_hash for e in chunk])
            if root != block.merkle_root or block.previous_block_hash != previous_hash:
                return {"valid": False, "reason": f"Merkle/block-chain verification failed at block {block.block_index}.", "block_index": block.block_index}
            expected = _sha256(json.dumps({
                "block_index": block.block_index,
                "first_sequence_id": block.first_sequence_id,
                "last_sequence_id": block.last_sequence_id,
                "previous_block_hash": block.previous_block_hash,
                "merkle_root": block.merkle_root,
                "entry_count": block.entry_count,
            }, sort_keys=True, separators=(",", ":")))
            if expected != block.block_hash:
                return {"valid": False, "reason": f"Block hash mismatch at block {block.block_index}.", "block_index": block.block_index}

            covered_entry_ids.update(entry.id for entry in chunk)
            previous_last_sequence = block.last_sequence_id
            previous_hash = block.block_hash

        entry_ids = {entry.id for entry in entries}
        unsealed = sorted(entry_ids - covered_entry_ids)
        if unsealed:
            return {
                "valid": False,
                "reason": "One or more evidence ledger entries are not covered by any Merkle block.",
                "unsealed_sequence_ids": unsealed[:100],
                "unsealed_count": len(unsealed),
                "entry_count": len(entries),
                "block_count": len(blocks),
                "head_block_hash": previous_hash,
            }

        return {
            "valid": True,
            "block_count": len(blocks),
            "entry_count": len(entries),
            "head_block_hash": previous_hash,
            "merkle_roots": [b.merkle_root for b in blocks[-10:]],
        }



class CollectionService:
    """Configurable multi-source collector for HTTP, JSON, RSS, HTML and Tor HTTP feeds.

    Sources are explicitly registered and are expected to be owned/authorized or public
    feeds intended for automated retrieval. No hard-coded dark-web targets are shipped.
    """

    def __init__(self, db):
        self.db = db

    @staticmethod
    def _allowed_host(url: str, source: CollectionSource) -> bool:
        host = (urlparse(url).hostname or "").lower()
        configured = {
            str(x).strip().lower()
            for x in (source.parser_config or {}).get("allowed_hosts", [])
            if str(x).strip()
        }
        global_allowed = {
            x.strip().lower()
            for x in settings.COLLECTION_ALLOWED_HOSTS.split(",")
            if x.strip()
        }
        onion_allowed = {
            x.strip().lower()
            for x in settings.TOR_ALLOWED_ONION_HOSTS.split(",")
            if x.strip()
        }
        # Tor sources must pass the dedicated onion allowlist even when a
        # per-source parser allowlist is present; this prevents that optional
        # setting from bypassing the Tor scope boundary.
        if source.kind == "tor_http":
            return host.endswith(".onion") and host in onion_allowed
        if host in configured or host in global_allowed:
            return True
        return False

    def _request(self, source: CollectionSource) -> tuple[int, str, str]:
        if not self._allowed_host(source.url, source):
            raise ValueError(f"Source host is not allowlisted: {urlparse(source.url).hostname}")
        headers = {"User-Agent": "DeCypher-Collector/1.0", **(source.headers or {})}
        proxies = None
        if source.kind == "tor_http":
            if not settings.TOR_SOCKS5_PROXY:
                raise ValueError("TOR_SOCKS5_PROXY is not configured.")
            parsed = urlparse(source.url)
            if not parsed.hostname or not parsed.hostname.endswith(".onion"):
                raise ValueError("tor_http sources must target an allowlisted .onion host.")
            proxies = {"http": settings.TOR_SOCKS5_PROXY, "https": settings.TOR_SOCKS5_PROXY}
        with requests.get(
            source.url,
            headers=headers,
            timeout=settings.COLLECTION_TIMEOUT_SECONDS,
            allow_redirects=False,
            verify=settings.SCANNER_TLS_VERIFY,
            proxies=proxies,
            stream=True,
        ) as response:
            response.raise_for_status()
            raw = _read_limited_response(response, settings.COLLECTION_MAX_RESPONSE_BYTES)
            status_code = response.status_code
            content_type = response.headers.get("content-type", "")
            encoding = response.encoding or "utf-8"
        return status_code, content_type, raw.decode(encoding, errors="replace")

    @staticmethod
    def _parse_rss(body: str) -> list[dict[str, Any]]:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(body)
        results = []
        for item in root.findall(".//item"):
            results.append({
                "title": item.findtext("title"),
                "link": item.findtext("link"),
                "description": item.findtext("description"),
                "timestamp": item.findtext("pubDate"),
            })
        return results

    @staticmethod
    def _parse_json(body: str) -> list[dict[str, Any]]:
        payload = json.loads(body)
        if isinstance(payload, list):
            return [item if isinstance(item, dict) else {"value": item} for item in payload]
        if isinstance(payload, dict):
            for key in ("items", "results", "data", "records"):
                if isinstance(payload.get(key), list):
                    return [item if isinstance(item, dict) else {"value": item} for item in payload[key]]
            return [payload]
        return [{"value": payload}]

    @staticmethod
    def _parse_html(body: str) -> list[dict[str, Any]]:
        title = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
        links = re.findall(r'href=[\'"]([^\'"]+)[\'"]', body, re.I)
        text = re.sub(r"<[^>]+>", " ", body)
        text = re.sub(r"\s+", " ", text).strip()
        return [{
            "title": re.sub(r"\s+", " ", title.group(1)).strip() if title else None,
            "link": links[0] if links else None,
            "description": text[:2000],
        }]

    @staticmethod
    def _extract_entities(item: dict[str, Any], source_name: str) -> list[tuple[str, str, dict[str, Any]]]:
        text = json.dumps(item, ensure_ascii=False)
        found: list[tuple[str, str, dict[str, Any]]] = []
        for wallet in re.findall(r"\b(?:bc1|[13])[a-zA-Z0-9]{20,80}\b", text):
            found.append(("wallet", wallet, {"source_item": item}))
        for pgp in re.findall(r"\b[A-Fa-f0-9]{40}\b", text):
            found.append(("pgp", pgp.upper(), {"source_item": item}))
        for onion in re.findall(r"\b[a-z2-7]{56}\.onion\b", text.lower()):
            found.append(("domain", onion, {"source_item": item}))
        for handle in re.findall(r"@[a-zA-Z0-9_.-]{3,64}", text):
            found.append(("handle", handle[1:], {"source_item": item}))
        return found

    def run_source(self, source: CollectionSource) -> dict[str, Any]:
        run = CollectionRun(source_id=source.id, status="running")
        self.db.add(run)
        self.db.flush()
        try:
            _, content_type, body = self._request(source)
            if source.kind == "rss":
                items = self._parse_rss(body)
            elif source.kind == "json":
                items = self._parse_json(body)
            else:
                items = self._parse_html(body)
            created_obs = 0
            created_entities = 0
            new_observation_rows: list[dict[str, Any]] = []
            source_label = f"collection:{source.name}"
            for item in items:
                item_json = json.dumps(item, sort_keys=True, default=str)
                obs_id = f"collect_{source.id}_{_sha256(item_json)[:24]}"
                observed_at = None
                raw_date = item.get("timestamp") or item.get("published") or item.get("date")
                if raw_date:
                    try:
                        observed_at = parsedate_to_datetime(str(raw_date))
                    except Exception:
                        try:
                            observed_at = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
                        except Exception:
                            observed_at = None
                observation = Observation(
                    observation_id=obs_id,
                    indicator_type="collection_item",
                    detected=True,
                    value=(item.get("title") or item.get("value") or "")[:512],
                    target=source.actor_id or source.url,
                    source=source_label,
                    timestamp=observed_at or utc_now(),
                    confidence=float((source.parser_config or {}).get("default_confidence", 0.65)),
                    description=str(item.get("description") or item.get("title") or item)[:4000],
                )
                existing = self.db.query(Observation).filter(Observation.observation_id == obs_id).first()
                if existing is None:
                    self.db.add(observation)
                    self.db.flush()
                    new_observation_rows.append({
                        "observation_id": observation.observation_id,
                        "indicator_type": observation.indicator_type,
                        "detected": observation.detected,
                        "value": observation.value,
                        "target": observation.target,
                        "source": observation.source,
                        "timestamp": observation.timestamp,
                        "confidence": observation.confidence,
                        "description": observation.description,
                    })
                    created_obs += 1

                # Entity extraction is deliberately independent of observation
                # deduplication. A previous partial run may have persisted the
                # observation but failed before creating its extracted entities.
                for entity_type, canonical, metadata in self._extract_entities(item, source.name):
                    entity = self.db.query(ExternalEntity).filter_by(
                        entity_type=entity_type, canonical_value=canonical, source=source_label
                    ).first()
                    if entity is None:
                        entity = ExternalEntity(
                            entity_type=entity_type,
                            canonical_value=canonical,
                            display_name=canonical,
                            source=source_label,
                            confidence=observation.confidence,
                            entity_metadata=metadata,
                        )
                        self.db.add(entity)
                        self.db.flush()
                        created_entities += 1
            if new_observation_rows:
                EvidenceLedgerService(self.db).append_missing_for_observations(
                    new_observation_rows,
                    actor_id=source.actor_id,
                    created_by=f"collector:{source.name}",
                )

            run.items_seen = len(items)
            run.observations_created = created_obs
            run.entities_created = created_entities
            run.status = "completed"
            run.finished_at = utc_now()
            source.last_run_at = run.finished_at
            source.last_status = "completed"
            source.last_error = None
            source.next_run_at = run.finished_at + timedelta(
                minutes=max(1, int(source.interval_minutes or 15))
            )
            self.db.commit()
            # Resolve newly extracted entities against the known actor corpus,
            # even when a source is not pre-assigned to one actor. These are
            # candidate evidence links, never identity determinations.
            candidate_links = []
            if created_obs or created_entities:
                try:
                    candidate_links = EntityLinkageService(self.db).link_recent_source(
                        source_label=source_label,
                    )
                except Exception as exc:
                    self.db.rollback()
                    print(f"[collection] Entity resolution warning: {exc}")

            affected_actor_ids = sorted({row["actor_id"] for row in candidate_links if row.get("actor_id")})
            if source.actor_id:
                affected_actor_ids = sorted(set(affected_actor_ids) | {source.actor_id})

            if new_observation_rows and source.actor_id:
                try:
                    from app.services import graph_service
                    graph_service.sync_actor_observations(source.actor_id, new_observation_rows)
                except Exception as exc:
                    # PostgreSQL remains authoritative; graph projection can be retried.
                    print(f"[collection] Neo4j observation projection warning: {exc}")

            if candidate_links:
                try:
                    from app.services import graph_service
                    graph_service.sync_external_entity_links(candidate_links)
                except Exception as exc:
                    print(f"[collection] Neo4j entity-link projection warning: {exc}")

            # Recompute evidence-only actor correlations after new source evidence
            # is available. Correlation scores remain triage signals, not identity probabilities.
            for linked_actor_id in affected_actor_ids:
                try:
                    from app.services.correlation_service import CorrelationService
                    CorrelationService(self.db).correlate_actor(linked_actor_id, persist=True)
                except Exception as exc:
                    print(f"[collection] Correlation refresh warning for {linked_actor_id}: {exc}")

            alert_error = None
            if created_obs:
                try:
                    AlertService(self.db).create(
                        alert_type="collection_update",
                        severity="medium",
                        title=f"New intelligence from {source.name}",
                        message=f"{created_obs} new evidence item(s) were collected.",
                        actor_id=source.actor_id,
                        payload={"source_id": source.id, "run_id": run.id, "observations_created": created_obs},
                    )
                    self.db.commit()
                except Exception as exc:
                    # Collection/evidence state was already committed above.
                    # Alert persistence is additive and must not retroactively
                    # turn a successful collection run into a failed one.
                    self.db.rollback()
                    alert_error = str(exc)[:500]
                    print(f"[collection] Alert persistence failed: {exc}")
            result = {
                "run_id": run.id,
                "items_seen": len(items),
                "observations_created": created_obs,
                "entities_created": created_entities,
            }
            if alert_error:
                result["alert_error"] = alert_error
            return result
        except Exception as exc:
            self.db.rollback()
            run = self.db.query(CollectionRun).filter(CollectionRun.id == run.id).first()
            if run:
                run.status = "failed"
                run.finished_at = utc_now()
                run.error = str(exc)[:2000]
            source = self.db.query(CollectionSource).filter(CollectionSource.id == source.id).first()
            if source:
                source.last_status = "failed"
                source.last_error = str(exc)[:2000]
                retry_minutes = min(5, max(1, int(source.interval_minutes or 15)))
                source.next_run_at = utc_now() + timedelta(minutes=retry_minutes)
            self.db.commit()
            raise


class TorIntelligenceService:
    """Opt-in Tor collection and descriptor analysis for allowlisted/authorized sources."""

    def inspect_onion(self, url: str) -> dict[str, Any]:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        allowed = {x.strip().lower() for x in settings.TOR_ALLOWED_ONION_HOSTS.split(",") if x.strip()}
        if not host.endswith(".onion") or host not in allowed:
            raise ValueError("Only explicitly allowlisted .onion hosts may be inspected.")
        if parsed.username or parsed.password:
            raise ValueError("Credentials embedded in Tor inspection URLs are not allowed.")
        if not settings.TOR_SOCKS5_PROXY:
            raise ValueError("TOR_SOCKS5_PROXY is not configured.")
        proxies = {"http": settings.TOR_SOCKS5_PROXY, "https": settings.TOR_SOCKS5_PROXY}
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Tor inspection requires an http:// or https:// URL.")
        with requests.get(
            url,
            timeout=settings.TOR_TIMEOUT_SECONDS,
            allow_redirects=False,
            proxies=proxies,
            headers={"User-Agent": "DeCypher-Tor-Inspector/1.0"},
            stream=True,
        ) as response:
            raw = _read_limited_response(response, settings.TOR_MAX_RESPONSE_BYTES)
            body = raw.decode(response.encoding or "utf-8", errors="replace")
            title_match = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
            return {
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type"),
                "content_sha256": _sha256(raw),
                "content_length": len(raw),
                "server": response.headers.get("server"),
                "title": title_match.group(1).strip() if title_match else None,
                "observed_at": utc_now().isoformat(),
            }

    @staticmethod
    def parse_descriptor(descriptor_text: str) -> dict[str, Any]:
        """Parse a Tor relay server descriptor and report conservative consistency checks.

        This parser does not deanonymize onion services. It validates selected
        public relay-descriptor fields and reports malformed or non-public
        advertised router addresses as reviewable indicators.
        """
        lines = [line.strip() for line in descriptor_text.splitlines() if line.strip()]
        result: dict[str, Any] = {
            "descriptor_type": "tor_relay_server_descriptor",
            "router": None,
            "published": None,
            "platform": None,
            "protocols": {},
            "raw_lines": len(lines),
            "anomalies": [],
        }
        for line in lines:
            if line.startswith("router "):
                parts = line.split()
                result["router"] = {
                    "nickname": parts[1] if len(parts) > 1 else None,
                    "address": parts[2] if len(parts) > 2 else None,
                    "or_ports": parts[3:] if len(parts) > 3 else [],
                }
            elif line.startswith("published "):
                result["published"] = line[len("published "):]
            elif line.startswith("platform "):
                result["platform"] = line[len("platform "):]
            elif line.startswith("proto "):
                for token in line[len("proto "):].split():
                    if "=" in token:
                        key, value = token.split("=", 1)
                        result["protocols"][key] = value

        anomalies = result["anomalies"]
        router = result["router"]
        if not router:
            anomalies.append({"code": "missing_router_line", "severity": "review", "detail": "Descriptor has no router declaration."})
        else:
            address = router.get("address")
            try:
                parsed_address = ipaddress.ip_address(address)
                if not parsed_address.is_global:
                    anomalies.append({
                        "code": "non_global_router_address",
                        "severity": "review",
                        "detail": "Advertised relay address is not globally routable.",
                    })
            except ValueError:
                anomalies.append({"code": "invalid_router_address", "severity": "review", "detail": "Router address is not a valid IP address."})
            ports = router.get("or_ports") or []
            if not ports:
                anomalies.append({"code": "missing_or_port", "severity": "review", "detail": "Router declaration has no OR port."})
            else:
                try:
                    if not 1 <= int(ports[0]) <= 65535:
                        raise ValueError
                except (TypeError, ValueError):
                    anomalies.append({"code": "invalid_or_port", "severity": "review", "detail": "Router OR port is outside the valid TCP port range."})

        if not result["published"]:
            anomalies.append({"code": "missing_published_timestamp", "severity": "review", "detail": "Descriptor has no published timestamp."})
        else:
            try:
                datetime.strptime(result["published"], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                anomalies.append({"code": "invalid_published_timestamp", "severity": "review", "detail": "Published timestamp does not match the Tor descriptor format."})

        result["consistency_status"] = (
            "insufficient_data" if not lines
            else "review_required" if anomalies
            else "no_basic_inconsistency_detected"
        )
        result["descriptor_sha256"] = _sha256(descriptor_text)
        return result


class StylometryDiscoveryService:
    def __init__(self, db):
        self.db = db

    def discover(self, limit: int = 200, actor_id: str | None = None) -> list[dict[str, Any]]:
        query = self.db.query(DarkWebHandle)
        if actor_id:
            actor = (
                self.db.query(Actor)
                .filter(func.lower(Actor.actor_id) == actor_id.lower())
                .first()
            )
            if actor is None:
                return []
            actor_id = actor.actor_id
            query = query.filter(DarkWebHandle.actor_id == actor_id)
        handles = query.order_by(DarkWebHandle.id.asc()).limit(120).all()
        groups: dict[str, list[DarkWebHandle]] = defaultdict(list)
        for handle in handles:
            groups[(handle.platform or "unknown").lower()].append(handle)
        candidates: list[tuple[DarkWebHandle, DarkWebHandle]] = []
        for group in groups.values():
            group = sorted(group, key=lambda item: hashlib.sha256((item.source_handle_id or str(item.id)).encode()).hexdigest())
            for i in range(len(group)):
                for j in range(i + 1, min(len(group), i + 6)):
                    if group[i].handle != group[j].handle:
                        candidates.append((group[i], group[j]))
        candidates = candidates[: max(1, min(limit, 1000))]
        results = []
        for a, b in candidates:
            try:
                compared = nlp_service.compare(a.handle, b.handle)
            except Exception as exc:
                compared = {"similarity_score": 0.0, "is_same_author": False, "engine_status": "error", "error": str(exc)}
            values = {
                "similarity": float(compared.get("similarity_score") or 0.0),
                "same_author": bool(compared.get("is_same_author")),
                "model_status": str(compared.get("engine_status") or "unknown"),
                "evidence": {
                    "shared_markers": compared.get("shared_markers", []),
                    "threshold_used": compared.get("threshold_used"),
                },
            }
            query = self.db.query(StylometryDiscovery).filter(
                StylometryDiscovery.handle_a == a.handle,
                StylometryDiscovery.handle_b == b.handle,
            )
            if a.actor_id is None:
                query = query.filter(StylometryDiscovery.actor_a.is_(None))
            else:
                query = query.filter(StylometryDiscovery.actor_a == a.actor_id)
            if b.actor_id is None:
                query = query.filter(StylometryDiscovery.actor_b.is_(None))
            else:
                query = query.filter(StylometryDiscovery.actor_b == b.actor_id)
            row = query.first()
            if row is None:
                row = StylometryDiscovery(
                    handle_a=a.handle,
                    handle_b=b.handle,
                    actor_a=a.actor_id,
                    actor_b=b.actor_id,
                    **values,
                )
                self.db.add(row)
            else:
                row.similarity = values["similarity"]
                row.same_author = values["same_author"]
                row.model_status = values["model_status"]
                row.evidence = values["evidence"]
            results.append({
                "handle_a": a.handle,
                "handle_b": b.handle,
                "actor_a": a.actor_id,
                "actor_b": b.actor_id,
                "similarity": row.similarity,
                "same_author": row.same_author,
                "model_status": row.model_status,
                "evidence": row.evidence,
            })
        self.db.commit()
        results.sort(key=lambda item: item["similarity"], reverse=True)
        return results


class EntityLinkageService:
    def __init__(self, db):
        self.db = db

    def link_recent_source(self, source_label: str) -> list[dict[str, Any]]:
        """Link newly collected entities to existing records using exact identifiers.

        Matching is intentionally conservative: handle, wallet, PGP fingerprint,
        and registered scan-host equality create candidate links. It never merges
        actor records or asserts that a candidate is a confirmed identity.
        """
        from app.models.sql_models import Wallet, ScanTarget

        query = self.db.query(ExternalEntity).filter(ExternalEntity.source == source_label)
        entities = query.order_by(ExternalEntity.id.asc()).all()
        actors = self.db.query(Actor).all()
        handles = self.db.query(DarkWebHandle).all()
        wallets = self.db.query(Wallet).all()
        targets = self.db.query(ScanTarget).all()

        by_actor: dict[str, dict[str, set[str]]] = {
            actor.actor_id: {"handle": set(), "wallet": set(), "pgp": set(), "domain": set()}
            for actor in actors
        }
        for actor in actors:
            by_actor[actor.actor_id]["handle"].add(_normal(actor.primary_handle))
        for handle in handles:
            if handle.actor_id in by_actor:
                by_actor[handle.actor_id]["handle"].add(_normal(handle.handle))
                for key in handle.pgp_keys:
                    if key.fingerprint:
                        by_actor[handle.actor_id]["pgp"].add(key.fingerprint.lower())
        for wallet in wallets:
            if wallet.actor_id in by_actor and wallet.address:
                by_actor[wallet.actor_id]["wallet"].add(wallet.address.lower())
        for target in targets:
            if target.actor_id in by_actor:
                host = urlparse(target.target_url).hostname
                if host:
                    by_actor[target.actor_id]["domain"].add(host.lower())

        results: list[dict[str, Any]] = []
        for entity in entities:
            canonical = str(entity.canonical_value or "")
            normalized = _normal(canonical)
            for actor_id, values in by_actor.items():
                matched = False
                if entity.entity_type == "handle":
                    matched = bool(normalized and normalized in values["handle"])
                elif entity.entity_type == "wallet":
                    matched = canonical.lower() in values["wallet"]
                elif entity.entity_type == "pgp":
                    matched = canonical.lower() in values["pgp"]
                elif entity.entity_type == "domain":
                    matched = canonical.lower() in values["domain"]
                if not matched:
                    continue

                existing = self.db.query(EntityLink).filter_by(
                    actor_id=actor_id, entity_id=entity.id
                ).first()
                explanation = {
                    "entity": canonical,
                    "source": entity.source,
                    "basis": "exact_identifier_match",
                    "identity_status": "candidate_only",
                }
                if existing:
                    existing.score = 1.0
                    existing.match_type = f"exact_{entity.entity_type}"
                    existing.explanation = explanation
                else:
                    self.db.add(EntityLink(
                        actor_id=actor_id,
                        entity_id=entity.id,
                        score=1.0,
                        match_type=f"exact_{entity.entity_type}",
                        explanation=explanation,
                    ))
                results.append({
                    "actor_id": actor_id,
                    "entity_id": entity.id,
                    "entity_type": entity.entity_type,
                    "canonical_value": canonical,
                    "source": entity.source,
                    "score": 1.0,
                    "match_type": f"exact_{entity.entity_type}",
                    "identity_status": "candidate_only",
                })
        self.db.commit()
        return results

    def link_actor(self, actor_id: str, min_score: float = 0.70) -> list[dict[str, Any]]:
        actor = (
            self.db.query(Actor)
            .filter(func.lower(Actor.actor_id) == actor_id.lower())
            .first()
        )
        if actor is None:
            raise ValueError(f"Actor '{actor_id}' not found.")
        actor_id = actor.actor_id
        handles = self.db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor_id).all()
        values = {
            "handle": {_normal(actor.primary_handle), *[_normal(h.handle) for h in handles]},
            "wallet": set(),
            "pgp": set(),
            "domain": set(),
        }
        from app.models.sql_models import Wallet
        values["wallet"] = {str(w.address).lower() for w in self.db.query(Wallet).filter(Wallet.actor_id == actor_id).all() if w.address}
        for handle in handles:
            values["pgp"].update((key.fingerprint or "").lower() for key in handle.pgp_keys)
        for target in actor.scan_targets:
            host = urlparse(target.target_url).hostname
            if host:
                values["domain"].add(host.lower())

        entities = self.db.query(ExternalEntity).all()
        links = []
        for entity in entities:
            canonical = str(entity.canonical_value or "")
            normalized = _normal(canonical)
            candidates = []
            if entity.entity_type == "handle" and normalized in values["handle"]:
                candidates.append((1.0, "exact_handle"))
            elif entity.entity_type == "wallet" and canonical.lower() in values["wallet"]:
                candidates.append((1.0, "exact_wallet"))
            elif entity.entity_type == "pgp" and canonical.lower() in values["pgp"]:
                candidates.append((1.0, "exact_pgp"))
            elif entity.entity_type == "domain" and canonical.lower() in values["domain"]:
                candidates.append((1.0, "exact_domain"))
            elif entity.entity_type in {"handle", "domain"} and normalized:
                for target in values[entity.entity_type]:
                    if normalized == target or (len(normalized) >= 6 and (normalized in target or target in normalized)):
                        candidates.append((0.78, "normalized_similarity"))
                        break
            if not candidates:
                continue
            score, match_type = max(candidates, key=lambda item: item[0])
            if score < min_score:
                continue
            existing = self.db.query(EntityLink).filter_by(actor_id=actor_id, entity_id=entity.id).first()
            if existing:
                existing.score = score
                existing.match_type = match_type
                existing.explanation = {"entity": canonical, "source": entity.source}
            else:
                self.db.add(EntityLink(
                    actor_id=actor_id,
                    entity_id=entity.id,
                    score=score,
                    match_type=match_type,
                    explanation={"entity": canonical, "source": entity.source},
                ))
            links.append({
                "entity_id": entity.id,
                "entity_type": entity.entity_type,
                "canonical_value": canonical,
                "source": entity.source,
                "score": score,
                "match_type": match_type,
            })
        self.db.commit()
        return sorted(links, key=lambda row: row["score"], reverse=True)


class MediaCorrelationService:
    def __init__(self, db):
        self.db = db

    def ingest(self, media_id: str, data_url: str, source: str, actor_id: str | None = None) -> dict[str, Any]:
        if "," in data_url:
            encoded = data_url.split(",", 1)[1]
        else:
            encoded = data_url
        data = base64.b64decode(encoded, validate=True)
        if len(data) > settings.MEDIA_MAX_BYTES:
            raise ValueError(f"Media exceeds {settings.MEDIA_MAX_BYTES} byte limit.")
        sha = _sha256(data)
        phash, width, height, mime = image_perceptual_hash(data)
        row = self.db.query(MediaEvidence).filter_by(media_id=media_id).first()
        if row is None:
            row = MediaEvidence(
                media_id=media_id,
                actor_id=actor_id,
                source=source,
                sha256=sha,
                phash=phash,
                mime_type=mime,
                width=width,
                height=height,
                metadata_json={"bytes": len(data)},
            )
            self.db.add(row)
        else:
            row.actor_id = actor_id
            row.source = source
            row.sha256 = sha
            row.phash = phash
            row.mime_type = mime
            row.width = width
            row.height = height
            row.metadata_json = {"bytes": len(data)}
        self.db.commit()
        return {
            "media_id": media_id, "sha256": sha, "phash": phash, "width": width,
            "height": height, "mime_type": mime, "source": source,
        }

    def compare(self, media_a: str, media_b: str) -> dict[str, Any]:
        a = self.db.query(MediaEvidence).filter_by(media_id=media_a).first()
        b = self.db.query(MediaEvidence).filter_by(media_id=media_b).first()
        if not a or not b:
            raise ValueError("Both media IDs must exist.")
        distance = phash_distance(a.phash, b.phash)
        similarity = round(max(0.0, 1.0 - distance / 64.0), 4)
        return {
            "media_a": media_a, "media_b": media_b, "distance": distance,
            "perceptual_similarity": similarity,
            "exact_sha256_match": a.sha256 == b.sha256,
            "interpretation": "Perceptual similarity is an image reuse/near-duplicate signal and does not prove common ownership.",
        }


class EvaluationService:
    def __init__(self, db):
        self.db = db

    def _sample_pairs(self, limit: int = 100) -> list[dict[str, Any]]:
        handles = self.db.query(DarkWebHandle).order_by(DarkWebHandle.id.asc()).limit(120).all()
        positives = []
        negatives = []
        by_actor: dict[str, list[DarkWebHandle]] = defaultdict(list)
        for handle in handles:
            if handle.actor_id:
                by_actor[str(handle.actor_id)].append(handle)
        actor_groups = list(by_actor.values())
        for group in actor_groups:
            if len(group) >= 2:
                positives.append((group[0], group[1], 1))
        flat = [h for group in actor_groups for h in group]
        for i in range(min(len(flat), 80)):
            for j in range(i + 1, min(len(flat), i + 8)):
                if flat[i].actor_id != flat[j].actor_id:
                    negatives.append((flat[i], flat[j], 0))
                if len(negatives) >= limit * 2:
                    break
            if len(negatives) >= limit * 2:
                break
        pairs = (positives + negatives)[:max(2, limit)]
        return [{"a": a, "b": b, "label": label} for a, b, label in pairs]

    def calibration(self, pairs: int = 100) -> dict[str, Any]:
        rows = []
        for pair in self._sample_pairs(pairs):
            result = nlp_service.compare(pair["a"].handle, pair["b"].handle)
            rows.append((float(result.get("similarity_score") or 0.0), pair["label"]))
        if not rows:
            return {"available": False, "reason": "No evaluation pairs were available."}
        bins = []
        brier = sum((score - label) ** 2 for score, label in rows) / len(rows)
        for lower in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
            upper = lower + 0.1
            bucket = [(s, y) for s, y in rows if (lower <= s < upper) or (upper == 1.0 and lower <= s <= upper)]
            if bucket:
                bins.append({
                    "lower": lower, "upper": upper,
                    "count": len(bucket),
                    "mean_score": round(sum(s for s, _ in bucket) / len(bucket), 4),
                    "empirical_match_rate": round(sum(y for _, y in bucket) / len(bucket), 4),
                })
        ece = sum((item["count"] / len(rows)) * abs(item["mean_score"] - item["empirical_match_rate"]) for item in bins)
        metrics = {
            "pairs": len(rows),
            "positive_pairs": sum(y for _, y in rows),
            "negative_pairs": sum(1 - y for _, y in rows),
            "brier_score": round(brier, 5),
            "expected_calibration_error": round(ece, 5),
            "bins": bins,
            "model_status": nlp_service.engine_status,
            "interpretation": "Diagnostic calibration of stylometry similarity against bundled synthetic actor labels; it does not calibrate the broader evidence-fusion score for real-world identity probability.",
        }
        run = EvaluationRun(evaluation_type="stylometry_calibration", source="synthetic_dataset", metrics=metrics)
        self.db.add(run)
        self.db.commit()
        return metrics

    def historical_cases(self, cases: list[dict[str, Any]]) -> dict[str, Any]:
        scored = []
        for case in cases[:500]:
            try:
                result = nlp_service.compare(case["handle_a"], case["handle_b"])
                score = float(result.get("similarity_score") or 0.0)
                predicted = score >= float(case.get("threshold", 0.65))
                expected = bool(case["expected_same_actor"])
                scored.append({"case_id": case.get("case_id", str(uuid.uuid4())), "score": score, "expected": expected, "predicted": predicted})
            except Exception as exc:
                scored.append({"case_id": case.get("case_id", str(uuid.uuid4())), "error": str(exc)})
        valid = [row for row in scored if "error" not in row]
        tp = sum(1 for row in valid if row["predicted"] and row["expected"])
        fp = sum(1 for row in valid if row["predicted"] and not row["expected"])
        fn = sum(1 for row in valid if not row["predicted"] and row["expected"])
        tn = sum(1 for row in valid if not row["predicted"] and not row["expected"])
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        metrics = {
            "cases": len(valid), "errors": len(scored) - len(valid),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(precision, 4), "recall": round(recall, 4),
            "f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0,
            "source": "user-supplied public/historical case manifest",
            "interpretation": "Retrospective validation only; use with documented provenance and do not treat it as a current identity probability benchmark.",
        }
        run = EvaluationRun(evaluation_type="historical_case_validation", source="public_case_manifest", metrics=metrics)
        self.db.add(run)
        self.db.commit()
        return {"metrics": metrics, "cases": scored}


class AlertService:
    def __init__(self, db):
        self.db = db

    def create(self, *, alert_type: str, severity: str, title: str, message: str, actor_id: str | None = None, payload: dict | None = None) -> Alert:
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            actor_id=actor_id,
            payload=payload or {},
        )
        self.db.add(alert)
        self.db.flush()
        return alert
