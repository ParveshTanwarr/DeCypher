def map_observation(
    observation: dict,
    target_id: str
) -> dict:
    """
    Convert an infrastructure observation
    into the backend's expected format.
    """

    description = observation.get(
        "evidence",
        ""
    )

    clearnet_match = observation.get(
        "clearnet_match_domain"
    )

    if clearnet_match:
        description += (
            f" Potential clearnet match: "
            f"{clearnet_match}."
        )

    return {
        "observation_id": observation.get(
            "observation_id"
        ),
        "indicator_type": observation.get(
            "indicator_type",
            "infrastructure"
        ),
        "detected": observation.get(
            "detected",
            False
        ),
        "value": str(
            observation.get(
                "observed_value"
            )
            or ""
        ),
        "target": target_id,
        "source": observation.get(
            "source",
            "infra/scanner.py"
        ),
        "timestamp": observation.get(
            "scan_date"
        ),
        "confidence": observation.get(
            "confidence",
            0.0
        ),
        "description": description
    }


def map_observations(
    observations: list[dict],
    target_id: str
) -> list[dict]:
    """
    Convert multiple infrastructure observations
    into backend-compatible observations.
    """

    return [
        map_observation(
            observation,
            target_id
        )
        for observation in observations
    ]