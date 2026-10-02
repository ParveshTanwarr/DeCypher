"""Unit tests for authorized scanner target validation."""

import os

import pytest

from infra.scanner import scan_target, validate_scan_target


def test_scanner_rejects_external_host():
    with pytest.raises(ValueError, match="not in AUTOSCAN_ALLOWED_HOSTS"):
        validate_scan_target("https://example.com/")


def test_scanner_rejects_non_http_scheme():
    with pytest.raises(ValueError, match="http"):
        validate_scan_target("ftp://127.0.0.1/file")


def test_scanner_rejects_embedded_credentials():
    with pytest.raises(ValueError, match="Credentials"):
        validate_scan_target("http://user:password@127.0.0.1:8000/")


def test_scanner_accepts_allowlisted_loopback():
    original = os.environ.get("AUTOSCAN_ALLOWED_HOSTS")
    os.environ["AUTOSCAN_ALLOWED_HOSTS"] = "127.0.0.1,localhost"
    try:
        validate_scan_target("http://127.0.0.1:8000/")
        validate_scan_target("https://localhost:8443/")
    finally:
        if original is None:
            os.environ.pop("AUTOSCAN_ALLOWED_HOSTS", None)
        else:
            os.environ["AUTOSCAN_ALLOWED_HOSTS"] = original
