"""Regression tests for the autonomous scanning safety and scheduling layer."""

from datetime import datetime, timezone

from app.models.sql_models import ScanTarget
from app.workers.tasks import effective_scan_interval_minutes, validate_authorized_target


def _target(**overrides):
    values = {
        "name": "demo",
        "target_url": "http://127.0.0.1:9000/",
        "interval_minutes": 180,
        "priority_aware": True,
        "enabled": True,
        "next_run_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return ScanTarget(**values)


def test_autoscan_rejects_non_allowlisted_hosts():
    try:
        validate_authorized_target("https://example.com/")
    except ValueError as exc:
        assert "not in AUTOSCAN_ALLOWED_HOSTS" in str(exc)
    else:
        raise AssertionError("external target should be rejected")


def test_autoscan_rejects_non_http_scheme():
    try:
        validate_authorized_target("ftp://127.0.0.1/file")
    except ValueError as exc:
        assert "http://" in str(exc)
    else:
        raise AssertionError("non-HTTP target should be rejected")


def test_priority_aware_schedule_accelerates_high_priority():
    target = _target(interval_minutes=180, priority_aware=True)
    assert effective_scan_interval_minutes(target, 90) == 15
    assert effective_scan_interval_minutes(target, 75) == 30
    assert effective_scan_interval_minutes(target, 55) == 60
    assert effective_scan_interval_minutes(target, 20) == 180


def test_priority_aware_never_violates_five_minute_floor():
    target = _target(interval_minutes=1, priority_aware=True)
    assert effective_scan_interval_minutes(target, 100) == 5


def test_non_priority_aware_target_keeps_configured_interval():
    target = _target(interval_minutes=240, priority_aware=False)
    assert effective_scan_interval_minutes(target, 100) == 240
