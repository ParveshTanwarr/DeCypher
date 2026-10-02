import os

import requests


DESCRIPTOR_TIMING_MARKER = "DESCRIPTOR_TIMING_TEST"


def detect_descriptor_timing(base_url: str):
    """
    Check an authorized test target for a
    descriptor-timing indicator.

    Returns the timing marker if detected,
    otherwise None.
    """

    timing_url = (
        base_url.rstrip("/")
        + "/descriptor-timing"
    )

    try:
        response = requests.get(
            timing_url,
            timeout=int(os.getenv("SCANNER_CONNECT_TIMEOUT_SECONDS", "10")),
            verify=os.getenv("SCANNER_TLS_VERIFY", "true").strip().lower() not in {"0", "false", "no", "off"},
            allow_redirects=False,
        )

        if (
            response.status_code == 200
            and DESCRIPTOR_TIMING_MARKER in response.content[: int(os.getenv("SCANNER_MAX_RESPONSE_BYTES", "1000000"))].decode("utf-8", errors="ignore")
        ):
            return DESCRIPTOR_TIMING_MARKER

    except requests.RequestException:
        pass

    return None