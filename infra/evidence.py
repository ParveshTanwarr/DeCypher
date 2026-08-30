import json
import uuid
from pathlib import Path


EVIDENCE_DIR = Path("data") / "evidence"
def ensure_observation_ids(
    observations: list[dict]
) -> list[dict]:
    """
    Ensure every observation has a unique ID.
    """

    for observation in observations:
        if not observation.get("observation_id"):
            observation["observation_id"] = (
                "OBS-INFRA-"
                + uuid.uuid4().hex[:12].upper()
            )

    return observations


def save_observations(
    observations: list[dict],
    filename: str = "infrastructure_observations.json"
):
    """
    Save scanner observations as JSON.
    """

    observations = ensure_observation_ids(
        observations
    )

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