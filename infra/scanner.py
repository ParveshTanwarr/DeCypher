import requests
from datetime import datetime, timezone

from infra.detectors.banner import detect_banner
from infra.detectors.status_page import detect_status_page

def scan_target(url: str) -> list[dict]:
    """
    Scan an authorized target for infrastructure indicators.
    """

    observations = []

    # -------------------------------------------------
    # 1. Check for server banner
    # -------------------------------------------------

    try:
        response = requests.get(
            url,
            timeout=10
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
                "scan_date": datetime.now(timezone.utc).isoformat(),
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
            "scan_date": datetime.now(timezone.utc).isoformat(),
            "source": "authorized-test-service",
            "evidence": str(error)
        })

        return observations

     # -------------------------------------------------
    # 2. Check for exposed status page
    # -------------------------------------------------

    status_marker = detect_status_page(url)

    if status_marker:
        status_url = url.rstrip("/") + "/server-status"

        observations.append({
            "observation_id": None,
            "indicator_type": "exposed_status_page",
            "target": status_url,
            "detected": True,
            "observed_value": status_marker,
            "clearnet_match_domain": None,
            "confidence": 0.90,
            "scan_date": datetime.now(timezone.utc).isoformat(),
            "source": "authorized-test-service",
            "evidence": "Authorized test status page detected."
        })

    return observations


if __name__ == "__main__":
    results = scan_target(
        "http://127.0.0.1:8000/"
    )

    for result in results:
        print(result)