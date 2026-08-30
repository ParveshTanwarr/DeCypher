from infra.backend_client import send_observations


test_observation = {
    "observation_id": "OBS-INFRA-TEST-001",
    "indicator_type": "infrastructure",
    "detected": True,
    "value": "MOCK-SERVER-V1",
    "target": "TEST-ACTOR-001",
    "source": "infra/scanner.py",
    "timestamp": "2026-08-30T14:30:00Z",
    "confidence": 0.85,
    "description": "Controlled infrastructure integration test."
}


if __name__ == "__main__":
    result = send_observations(
        [test_observation]
    )

    print("Backend response:")
    print(result)