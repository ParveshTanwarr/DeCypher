import os
import re

import requests

from infra.detectors.response_utils import read_response_text


def _classify_status_page(body: str) -> str | None:
    """Recognize the controlled fixture or a conservative Apache mod_status signature."""
    if "EXPOSED_STATUS_PAGE_TEST" in body:
        return "EXPOSED_STATUS_PAGE_TEST"

    normalized = re.sub(r"\s+", " ", body).lower()
    apache_markers = (
        "apache server status",
        "server uptime:",
        "total accesses:",
        "scoreboard:",
    )
    # Require multiple independent page markers to avoid treating a generic
    # page containing one phrase as an exposed server-status endpoint.
    if sum(marker in normalized for marker in apache_markers) >= 3:
        return "apache_mod_status_signature"
    return None


def detect_status_page(base_url: str):
    """Check the authorized target's /server-status endpoint for known signatures.

    This only detects a response signature. It does not attempt authentication
    bypass, exploit a misconfiguration, or infer the origin IP of a Tor service.
    """
    status_url = base_url.rstrip("/") + "/server-status"
    try:
        with requests.get(
            status_url,
            timeout=int(os.getenv("SCANNER_CONNECT_TIMEOUT_SECONDS", "10")),
            verify=os.getenv("SCANNER_TLS_VERIFY", "true").strip().lower() not in {"0", "false", "no", "off"},
            allow_redirects=False,
            stream=True,
        ) as response:
            if response.status_code != 200:
                return None
            body = read_response_text(response)
            return _classify_status_page(body)
    except requests.RequestException:
        return None
