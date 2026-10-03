"""Unit tests for authorized scanner target validation."""

import os
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infra import scanner
from infra.scanner import validate_scan_target


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



def test_scanner_network_failure_is_reported_as_failed_scan(monkeypatch):
    monkeypatch.setenv("AUTOSCAN_ALLOWED_HOSTS", "127.0.0.1,localhost")

    def fail_request(*args, **kwargs):
        raise requests.ConnectionError("test target unavailable")

    monkeypatch.setattr(scanner.requests, "get", fail_request)

    with pytest.raises(RuntimeError, match="Authorized scan request failed"):
        scanner.scan_target("http://127.0.0.1:9000/")



def test_banner_detector_collects_standard_service_headers_without_calling_them_vulnerable():
    from types import SimpleNamespace
    from infra.detectors.banner import detect_banner

    response = SimpleNamespace(headers={"Server": "Apache/2.4.58", "X-Powered-By": "PHP"})
    assert detect_banner(response) == "Server: Apache/2.4.58"


def test_banner_detector_prefers_controlled_fixture_marker():
    from types import SimpleNamespace
    from infra.detectors.banner import detect_banner

    response = SimpleNamespace(headers={
        "X-DeCypher-Test-Banner": "DE-CYPHER-FIXTURE",
        "Server": "Apache/2.4.58",
    })
    assert detect_banner(response) == "DE-CYPHER-FIXTURE"


def test_status_detector_recognizes_apache_mod_status_signature_only_with_multiple_markers():
    from infra.detectors.status_page import _classify_status_page

    assert _classify_status_page(
        "Apache Server Status: Server uptime: 2 hours. Total accesses: 42. Scoreboard: _W"
    ) == "apache_mod_status_signature"
    assert _classify_status_page("A normal page mentions server uptime: once.") is None
