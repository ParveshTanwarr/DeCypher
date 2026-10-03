"""Shared safety policy for authorized scanner targets.

The backend queueing layer and the low-level scanner both use this validator so
validation cannot silently diverge between stages of a scan.
"""

from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse


def normalize_allowed_hosts(hosts: Iterable[str]) -> set[str]:
    return {
        str(host).strip().lower()
        for host in hosts
        if str(host).strip()
    }


def validate_scan_target(url: str, allowed_hosts: Iterable[str]) -> None:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(
            "Scan target must be a valid http:// or https:// URL with a hostname."
        )

    if parsed.username or parsed.password:
        raise ValueError("Credentials embedded in scan URLs are not allowed.")

    host = parsed.hostname.lower()
    allowed = normalize_allowed_hosts(allowed_hosts)

    if host not in allowed:
        allowed_display = ", ".join(sorted(allowed)) or "(none)"
        raise ValueError(
            f"Target host '{host}' is not in AUTOSCAN_ALLOWED_HOSTS. "
            f"Allowed hosts: {allowed_display}"
        )
