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
            timeout=10
        )

        if (
            response.status_code == 200
            and "EXPOSED_STATUS_PAGE_TEST"
            in response.text
        ):
            return "EXPOSED_STATUS_PAGE_TEST"

    except requests.RequestException:
        pass

    return None