"""Helpers for safely bounding scanner detector response reads."""

from __future__ import annotations

import os
import requests


def max_response_bytes() -> int:
    value = int(os.getenv("SCANNER_MAX_RESPONSE_BYTES", "1000000"))
    return max(1, value)


def read_response_text(response: requests.Response, limit: int | None = None) -> str:
    """Read at most the configured byte limit from a streaming response."""
    byte_limit = max_response_bytes() if limit is None else max(1, int(limit))
    chunks: list[bytes] = []
    total = 0

    for chunk in response.iter_content(chunk_size=min(8192, byte_limit)):
        if not chunk:
            continue
        remaining = byte_limit - total
        chunks.append(chunk[:remaining])
        total += min(len(chunk), remaining)
        if total >= byte_limit:
            break

    return b"".join(chunks).decode("utf-8", errors="ignore")
