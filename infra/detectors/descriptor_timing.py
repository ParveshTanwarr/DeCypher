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
            timeout=10,
            verify=False
        )

        if (
            response.status_code == 200
            and DESCRIPTOR_TIMING_MARKER
            in response.text
        ):
            return DESCRIPTOR_TIMING_MARKER

    except requests.RequestException:
        pass

    return None