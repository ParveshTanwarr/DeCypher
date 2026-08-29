def detect_banner(response):
    """
    Detect the controlled DeCypher test server banner.

    Returns the banner value if detected,
    otherwise None.
    """

    banner = response.headers.get(
        "X-DeCypher-Test-Banner"
    )

    return banner