import json
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
from infra.evidence import save_observations
from infra.observation_mapper import map_observations
from infra.backend_client import send_observations
from infra.target_policy import validate_scan_target as _validate_scan_target

import requests

from infra.detectors.banner import detect_banner
from infra.detectors.status_page import detect_status_page
from infra.detectors.certificate import (
    get_certificate_fingerprint,
    match_certificate_fingerprint
)
from infra.detectors.descriptor_timing import (
    detect_descriptor_timing
)


def _observation_id() -> str:
    return f"scanobs_{uuid.uuid4().hex[:12]}"


def _allowed_hosts() -> set[str]:
    return {
        item.strip().lower()
        for item in os.getenv("AUTOSCAN_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
        if item.strip()
    }


def validate_scan_target(url: str) -> None:
    _validate_scan_target(url, _allowed_hosts())


def _tls_verify() -> bool:
    value = os.getenv("SCANNER_TLS_VERIFY", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def scan_target(url: str) -> list[dict]:
    """Scan an allowlisted, authorized target for infrastructure indicators."""

    validate_scan_target(url)
    observations = []
    scan_date = datetime.now(timezone.utc).isoformat()

    try:
        with requests.get(
            url,
            timeout=int(os.getenv("SCANNER_CONNECT_TIMEOUT_SECONDS", "10")),
            verify=_tls_verify(),
            allow_redirects=False,
            stream=True,
        ) as response:
            banner = detect_banner(response)

            if banner:
                is_controlled_marker = bool(response.headers.get("X-DeCypher-Test-Banner"))
                observations.append({
                    "observation_id": _observation_id(),
                    "indicator_type": "default_banner" if is_controlled_marker else "service_banner",
                    "target": url,
                    "detected": True,
                    "observed_value": banner,
                    "clearnet_match_domain": None,
                    "confidence": 0.85 if is_controlled_marker else 0.55,
                    "scan_date": scan_date,
                    "source": "authorized_scan",
                    "evidence": (
                        "Controlled DeCypher test banner detected."
                        if is_controlled_marker
                        else "Service identification header collected; this is an observation, not a vulnerability verdict."
                    )
                })

    except requests.RequestException as error:
        # A failed network request is a failed scan, not an evidence finding.
        # Raise so the Celery task records the job/target as failed instead of
        # incorrectly marking an unreachable target as successfully scanned.
        raise RuntimeError(f"Authorized scan request failed: {error}") from error

    status_marker = detect_status_page(url)

    if status_marker:
        status_url = url.rstrip("/") + "/server-status"
        observations.append({
            "observation_id": _observation_id(),
            "indicator_type": "exposed_status_page",
            "target": status_url,
            "detected": True,
            "observed_value": status_marker,
            "clearnet_match_domain": None,
            "confidence": 0.90,
            "scan_date": scan_date,
            "source": "authorized_scan",
            "evidence": f"Authorized status endpoint matched the detector signature: {status_marker}."
        })

    if url.startswith("https://"):
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port or 443
        fingerprint = get_certificate_fingerprint(host, port)

        if fingerprint:
            try:
                known_certificates_path = Path(__file__).resolve().parent / "known_certificates.json"
                with open(known_certificates_path, "r", encoding="utf-8") as file:
                    known_certificates = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                known_certificates = {}

            clearnet_match = match_certificate_fingerprint(
                fingerprint,
                known_certificates
            )

            if clearnet_match:
                observations.append({
                    "observation_id": _observation_id(),
                    "indicator_type": "ssl_cert_reuse",
                    "target": url,
                    "detected": True,
                    "observed_value": fingerprint,
                    "clearnet_match_domain": clearnet_match,
                    "confidence": 0.90,
                    "scan_date": scan_date,
                    "source": "authorized-test-service",
                    "evidence": "TLS certificate fingerprint matched known infrastructure."
                })
            else:
                observations.append({
                    "observation_id": _observation_id(),
                    "indicator_type": "ssl_certificate",
                    "target": url,
                    "detected": True,
                    "observed_value": fingerprint,
                    "clearnet_match_domain": None,
                    "confidence": 0.80,
                    "scan_date": scan_date,
                    "source": "authorized-test-service",
                    "evidence": "TLS certificate fingerprint successfully collected."
                })

    timing_marker = detect_descriptor_timing(url)

    if timing_marker:
        timing_url = url.rstrip("/") + "/descriptor-timing"
        observations.append({
            "observation_id": _observation_id(),
            "indicator_type": "descriptor_timing",
            "target": timing_url,
            "detected": True,
            "observed_value": timing_marker,
            "clearnet_match_domain": None,
            "confidence": 0.75,
            "scan_date": scan_date,
            "source": "authorized-test-service",
            "evidence": f"Authorized descriptor timing endpoint returned the controlled marker: {timing_marker}."
        })

    return observations


if __name__ == "__main__":
    results = scan_target("https://127.0.0.1:8443/")

    for result in results:
        print(result)

    output_path = save_observations(results)
    print()
    print(f"Evidence saved to: {output_path}")

    mapped_observations = map_observations(results, "ACT-8821")
    backend_result = send_observations(mapped_observations)

    print()
    print("Backend response:")
    print(backend_result)
