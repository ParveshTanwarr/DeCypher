from datetime import date
from pathlib import Path

import pytest

from app.services.demo_data import (
    DemoDatasetValidationError,
    future_date_violations,
    validate_bundled_demo_data,
)


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
REFERENCE_DATE = date(2026, 10, 5)


def test_bundled_demo_dataset_has_no_future_dates():
    assert future_date_violations(DATA_DIR, REFERENCE_DATE) == []


def test_bundled_demo_dataset_fingerprint_is_stable():
    first = validate_bundled_demo_data(DATA_DIR, REFERENCE_DATE)
    second = validate_bundled_demo_data(DATA_DIR, REFERENCE_DATE)
    assert first == second
    assert len(first) == 64


def test_future_date_validator_rejects_future_rows(tmp_path):
    (tmp_path / "actors.csv").write_text("actor_id,risk_category\nA00001,drugs\n", encoding="utf-8")
    (tmp_path / "handles.csv").write_text(
        "handle_id,created_date,last_active_date\n"
        "H00001,2026-01-01,2026-10-06\n",
        encoding="utf-8",
    )
    (tmp_path / "wallets.csv").write_text(
        "wallet_address,handle_id,currency,tx_count,first_seen\n"
        "wallet,H00001,BTC,1,2026-01-01\n",
        encoding="utf-8",
    )
    (tmp_path / "infrastructure_indicators.csv").write_text(
        "indicator_id,scan_date\nI00001,2026-01-01\n",
        encoding="utf-8",
    )

    violations = future_date_violations(tmp_path, REFERENCE_DATE)
    assert len(violations) == 1
    assert violations[0]["file"] == "handles.csv"
    assert violations[0]["column"] == "last_active_date"

    with pytest.raises(DemoDatasetValidationError):
        validate_bundled_demo_data(tmp_path, REFERENCE_DATE)
