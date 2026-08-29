import requests
from datetime import datetime, timezone


def scan_target(url: str) -> dict:
    """
    Scan an authorized test target for known
    DeCypher infrastructure indicators.
    """

    try:
        response = requests.get(
            url,
            timeout=10
        )

        # HTTP headers are case-insensitive.
        banner = response.headers.get("X-DeCypher-Test-Banner")

        if banner:
            return {
                "indicator_type": "default_banner",
                "detected": True,
                "value": banner,
                "target": url,
                "source": "authorized-test-service",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "indicator_type": "default_banner",
            "detected": False,
            "value": None,
            "target": url,
            "source": "authorized-test-service",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except requests.RequestException as error:
        return {
            "indicator_type": "scan_error",
            "detected": False,
            "value": None,
            "target": url,
            "source": "authorized-test-service",
            "error": str(error),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


if __name__ == "__main__":
    result = scan_target("http://127.0.0.1:8000/")
    print(result)