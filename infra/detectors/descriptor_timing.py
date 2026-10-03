import os

import requests

from infra.detectors.response_utils import read_response_text


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
        with requests.get(
            timing_url,
            timeout=int(os.getenv("SCANNER_CONNECT_TIMEOUT_SECONDS", "10")),
            verify=os.getenv("SCANNER_TLS_VERIFY", "true").strip().lower() not in {"0", "false", "no", "off"},
            allow_redirects=False,
            stream=True,
        ) as response:
            body = read_response_text(response)
            if response.status_code == 200 and DESCRIPTOR_TIMING_MARKER in body:
                return DESCRIPTOR_TIMING_MARKER

    except requests.RequestException:
        pass

    return None