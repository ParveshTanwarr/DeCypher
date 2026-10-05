from __future__ import annotations

import csv
import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

DATASET_FILES: tuple[str, ...] = (
    "actors.csv",
    "handles.csv",
    "wallets.csv",
    "infrastructure_indicators.csv",
)

DATE_FIELDS: dict[str, tuple[str, ...]] = {
    "handles.csv": ("created_date", "last_active_date"),
    "wallets.csv": ("first_seen",),
    "infrastructure_indicators.csv": ("scan_date",),
}


class DemoDatasetValidationError(ValueError):
    """Raised when bundled synthetic demo data violates its time boundary."""


def dataset_fingerprint(data_dir: Path) -> str:
    """Return a stable SHA-256 fingerprint of the bundled demo inputs."""
    digest = hashlib.sha256()
    for filename in DATASET_FILES:
        path = data_dir / filename
        digest.update(filename.encode("utf-8"))
        digest.update(b"\0")
        if not path.exists():
            raise DemoDatasetValidationError(
                f"Required bundled dataset file is missing: {path}"
            )
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def future_date_violations(
    data_dir: Path,
    reference_date: date,
) -> list[dict[str, object]]:
    """Return source rows containing dates later than the demo reference date."""
    violations: list[dict[str, object]] = []

    for filename, columns in DATE_FIELDS.items():
        path = data_dir / filename
        if not path.exists():
            raise DemoDatasetValidationError(
                f"Required bundled dataset file is missing: {path}"
            )

        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for line_number, row in enumerate(reader, start=2):
                for column in columns:
                    raw = (row.get(column) or "").strip()
                    if not raw:
                        continue
                    try:
                        parsed = date.fromisoformat(raw[:10])
                    except ValueError:
                        violations.append(
                            {
                                "file": filename,
                                "line": line_number,
                                "column": column,
                                "value": raw,
                                "reason": "invalid_date",
                            }
                        )
                        continue

                    if parsed > reference_date:
                        violations.append(
                            {
                                "file": filename,
                                "line": line_number,
                                "column": column,
                                "value": raw,
                                "reason": "future_date",
                            }
                        )

    return violations


def validate_bundled_demo_data(
    data_dir: Path,
    reference_date: date,
) -> str:
    """Validate the bundled synthetic dataset and return its fingerprint."""
    violations = future_date_violations(data_dir, reference_date)
    if violations:
        preview = "; ".join(
            f"{item['file']}:{item['line']} {item['column']}={item['value']}"
            for item in violations[:10]
        )
        suffix = " ..." if len(violations) > 10 else ""
        raise DemoDatasetValidationError(
            f"Bundled demo data contains {len(violations)} invalid/future date value(s) "
            f"after {reference_date.isoformat()}: {preview}{suffix}"
        )

    return dataset_fingerprint(data_dir)
