import os

import requests

from infra.detectors.response_utils import read_response_text


def detect_status_page(base_url: str):
    """
    Check the authorized test target for an exposed
    status-page indicator.

    Returns the test marker if detected,
    otherwise None.
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
            body = read_response_text(response)
            if response.status_code == 200 and "EXPOSED_STATUS_PAGE_TEST" in body:
                return "EXPOSED_STATUS_PAGE_TEST"

    except requests.RequestException:
        pass

    return None