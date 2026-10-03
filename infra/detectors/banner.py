def detect_banner(response):
    """Return a bounded service banner from an authorized HTTP response.

    The controlled DeCypher marker is retained for deterministic tests. For
    ordinary services, collect only standard identification headers; a banner
    is an observation, not by itself a vulnerability finding.
    """
    marker = response.headers.get("X-DeCypher-Test-Banner")
    if marker:
        return str(marker).strip()[:256]

    for header in ("Server", "X-Powered-By", "Via"):
        value = response.headers.get(header)
        if value and str(value).strip():
            return f"{header}: {str(value).strip()[:220]}"
    return None
