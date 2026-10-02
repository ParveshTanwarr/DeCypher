import os

import requests


def detect_status_page(base_url: str):
    """
    Check the authorized test target for an exposed
    status-page indicator.

    Returns the test marker if detected,
    otherwise None.
    """

    status_url = base_url.rstrip("/") + "/server-status"

    try:
        response = requests.get(
            status_url,
            timeout=int(os.getenv("SCANNER_CONNECT_TIMEOUT_SECONDS", "10")),
            verify=os.getenv("SCANNER_TLS_VERIFY", "true").strip().lower() not in {"0", "false", "no", "off"},
            allow_redirects=False,
        )

        if (
            response.status_code == 200
            and "EXPOSED_STATUS_PAGE_TEST" in response.content[: int(os.getenv("SCANNER_MAX_RESPONSE_BYTES", "1000000"))].decode("utf-8", errors="ignore")
        ):
            return "EXPOSED_STATUS_PAGE_TEST"

    except requests.RequestException:
        pass

    return None