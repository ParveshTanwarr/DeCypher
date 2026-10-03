import os

import requests


BACKEND_BASE_URL = os.getenv("DECYPHER_BACKEND_URL", "http://localhost:8000")
# Demo defaults match the existing local investigator account. For a real
# deployment, set these environment variables to the dedicated service user.
SCANNER_USERNAME = os.getenv("DECYPHER_SCANNER_USERNAME", "scanner_service")
SCANNER_PASSWORD = os.getenv("DECYPHER_SCANNER_PASSWORD", "")


def _get_access_token() -> str:
    if not SCANNER_PASSWORD:
        raise RuntimeError(
            "DECYPHER_SCANNER_PASSWORD is not configured for the scanner service client."
        )
    response = requests.post(
        f"{BACKEND_BASE_URL}/auth/token",
        data={
            "username": SCANNER_USERNAME,
            "password": SCANNER_PASSWORD,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def send_observations(observations: list[dict]):
    """Send infrastructure observations to the authenticated backend."""
    token = _get_access_token()

    response = requests.post(
        f"{BACKEND_BASE_URL}/scanner/observations",
        json={"observations": observations},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )

    response.raise_for_status()
    return response.json()
