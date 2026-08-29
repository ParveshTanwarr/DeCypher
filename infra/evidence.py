import json
from pathlib import Path


EVIDENCE_DIR = Path("data") / "evidence"


def save_observations(
    observations: list[dict],
    filename: str = "infrastructure_observations.json"
):
    """
    Save scanner observations as a JSON file
    that can later be consumed by the backend.
    """

    EVIDENCE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = EVIDENCE_DIR / filename

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            observations,
            file,
            indent=2,
            ensure_ascii=False
        )

    return output_path