import json
from datetime import datetime, timezone
from urllib.parse import urlparse
from infra.evidence import save_observations
from infra.observation_mapper import map_observations
from infra.backend_client import send_observations

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


def scan_target(url: str) -> list[dict]:
    """
    Scan an authorized target for infrastructure indicators.
    """

    observations = []

    scan_date = datetime.now(
        timezone.utc
    ).isoformat()

    # -------------------------------------------------
    # 1. Check for server banner
    # -------------------------------------------------

    try:
        response = requests.get(
            url,
            timeout=10,
            verify=False
        )

        banner = detect_banner(response)

        if banner:
            observations.append({
                "observation_id": None,
                "indicator_type": "default_banner",
                "target": url,
                "detected": True,
                "observed_value": banner,
                "clearnet_match_domain": None,
                "confidence": 0.85,
                "scan_date": scan_date,
                "source": "authorized-test-service",
                "evidence": "Test server banner detected."
            })

    except requests.RequestException as error:
        observations.append({
            "observation_id": None,
            "indicator_type": "scan_error",
            "target": url,
            "detected": False,
            "observed_value": None,
            "clearnet_match_domain": None,
            "confidence": 0.0,
            "scan_date": scan_date,
            "source": "authorized-test-service",
            "evidence": str(error)
        })

        return observations

    # -------------------------------------------------
    # 2. Check for exposed status page
    # -------------------------------------------------

    status_marker = detect_status_page(url)

    if status_marker:
        status_url = (
            url.rstrip("/")
            + "/server-status"
        )

        observations.append({
            "observation_id": None,
            "indicator_type": "exposed_status_page",
            "target": status_url,
            "detected": True,
            "observed_value": status_marker,
            "clearnet_match_domain": None,
            "confidence": 0.90,
            "scan_date": scan_date,
            "source": "authorized-test-service",
            "evidence": "Authorized test status page detected."
        })

    # -------------------------------------------------
    # 3. Check SSL certificate
    # -------------------------------------------------

    if url.startswith("https://"):

        parsed_url = urlparse(url)

        host = parsed_url.hostname
        port = parsed_url.port or 443

        fingerprint = get_certificate_fingerprint(
            host,
            port
        )

        if fingerprint:

            try:
                with open(
                    "infra/known_certificates.json",
                    "r",
                    encoding="utf-8"
                ) as file:
                    known_certificates = json.load(file)

            except (FileNotFoundError, json.JSONDecodeError):
                known_certificates = {}

            clearnet_match = (
                match_certificate_fingerprint(
                    fingerprint,
                    known_certificates
                )
            )

            if clearnet_match:

                observations.append({
                    "observation_id": None,
                    "indicator_type": "ssl_cert_reuse",
                    "target": url,
                    "detected": True,
                    "observed_value": fingerprint,
                    "clearnet_match_domain": clearnet_match,
                    "confidence": 0.90,
                    "scan_date": scan_date,
                    "source": "authorized-test-service",
                    "evidence": (
                        "TLS certificate fingerprint "
                        "matched known infrastructure."
                    )
                })

            else:

                observations.append({
                    "observation_id": None,
                    "indicator_type": "ssl_certificate",
                    "target": url,
                    "detected": True,
                    "observed_value": fingerprint,
                    "clearnet_match_domain": None,
                    "confidence": 0.80,
                    "scan_date": scan_date,
                    "source": "authorized-test-service",
                    "evidence": (
                        "TLS certificate fingerprint "
                        "successfully collected."
                    )
                })

    # -------------------------------------------------
    # 4. Check descriptor timing
    # -------------------------------------------------

    timing_marker = detect_descriptor_timing(url)

    if timing_marker:

        timing_url = (
            url.rstrip("/")
            + "/descriptor-timing"
        )

        observations.append({
            "observation_id": None,
            "indicator_type": "descriptor_timing",
            "target": timing_url,
            "detected": True,
            "observed_value": timing_marker,
            "clearnet_match_domain": None,
            "confidence": 0.75,
            "scan_date": scan_date,
            "source": "authorized-test-service",
            "evidence": (
                "Authorized descriptor timing "
                "test signal detected."
            )
        })

    return observations


if __name__ == "__main__":

    results = scan_target(
        "https://127.0.0.1:8443/"
    )

    for result in results:
        print(result)

    output_path = save_observations(
        results
    )

    print()
    print(
        f"Evidence saved to: {output_path}"
    )

    # -------------------------------------------------
    # Send observations to backend
    # -------------------------------------------------

    mapped_observations = map_observations(
        results,
        "ACT-8821"
    )

    backend_result = send_observations(
        mapped_observations
    )

    print()
    print("Backend response:")
    print(backend_result)