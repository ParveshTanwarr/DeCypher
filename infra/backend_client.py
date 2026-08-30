import requests


BACKEND_URL = "http://localhost:8000/scanner/observations"


def send_observations(
    observations: list[dict]
):
    """
    Send infrastructure observations
    to the DeCypher backend.
    """

    payload = {
        "observations": observations
    }

    response = requests.post(
        BACKEND_URL,
        json=payload,
        timeout=10
    )

    response.raise_for_status()

    return response.json()