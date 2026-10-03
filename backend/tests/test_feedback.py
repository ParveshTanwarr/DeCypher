"""
Feedback endpoint regression tests: the renamed route, identity coming
from the verified token instead of a spoofable body field, and feedback
actually affecting an actor's confidence/priority score.
"""


def test_feedback_route_is_investigator_feedback(client, admin_headers):
    r = client.post(
        "/investigator/feedback",
        headers=admin_headers,
        json={"actor_id": "A00010", "verdict": "Confirmed"},
    )
    assert r.status_code == 201


def test_old_feedback_route_no_longer_exists(client, admin_headers):
    r = client.post("/feedback", headers=admin_headers, json={"actor_id": "A00010", "verdict": "Confirmed"})
    assert r.status_code == 404


def test_investigator_id_comes_from_token_not_body(client, analyst_headers):
    r = client.post(
        "/investigator/feedback",
        headers=analyst_headers,
        json={"actor_id": "A00011", "verdict": "Confirmed", "investigator_id": "someone_else_entirely"},
    )
    assert r.status_code == 201

    listing = client.get("/investigator/feedback", headers=analyst_headers, params={"actor_id": "A00011"}).json()
    assert listing[0]["investigator_id"] == "analyst"
    assert listing[0]["investigator_id"] != "someone_else_entirely"


def test_confirmed_feedback_increases_scores(client, admin_headers):
    before = client.get("/actors/A00012", headers=admin_headers).json()
    client.post(
        "/investigator/feedback",
        headers=admin_headers,
        json={"actor_id": "A00012", "verdict": "Confirmed - High Risk"},
    )
    after = client.get("/actors/A00012", headers=admin_headers).json()
    assert after["confidence_score"] > before["confidence_score"]
    assert after["priority_score"] > before["priority_score"]


def test_false_positive_feedback_decreases_scores(client, admin_headers):
    before = client.get("/actors/A00013", headers=admin_headers).json()
    client.post(
        "/investigator/feedback",
        headers=admin_headers,
        json={"actor_id": "A00013", "verdict": "False Positive"},
    )
    after = client.get("/actors/A00013", headers=admin_headers).json()
    assert after["confidence_score"] < before["confidence_score"]
    assert after["priority_score"] < before["priority_score"]


def test_feedback_for_nonexistent_actor_404s(client, admin_headers):
    r = client.post(
        "/investigator/feedback",
        headers=admin_headers,
        json={"actor_id": "DOES_NOT_EXIST", "verdict": "Confirmed"},
    )
    assert r.status_code == 404


def test_service_account_cannot_submit_investigator_feedback(client):
    login = client.post(
        "/auth/token",
        data={
            "username": "scanner_service",
            "password": "scanner_service_devkey_change_me",
        },
    )
    assert login.status_code == 200, login.text

    r = client.post(
        "/investigator/feedback",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        json={"actor_id": "A00014", "verdict": "Confirmed"},
    )
    assert r.status_code == 403


def test_repeated_feedback_does_not_compound(client, admin_headers):
    first = client.post(
        "/investigator/feedback",
        headers=admin_headers,
        json={"actor_id": "A00014", "verdict": "Confirmed"},
    )
    assert first.status_code == 201, first.text
    after_first = client.get("/actors/A00014", headers=admin_headers).json()

    second = client.post(
        "/investigator/feedback",
        headers=admin_headers,
        json={"actor_id": "A00014", "verdict": "Confirmed"},
    )
    assert second.status_code == 201, second.text
    after_second = client.get("/actors/A00014", headers=admin_headers).json()

    assert after_second["confidence_score"] == after_first["confidence_score"]
    assert after_second["priority_score"] == after_first["priority_score"]

    changed = client.post(
        "/investigator/feedback",
        headers=admin_headers,
        json={"actor_id": "A00014", "verdict": "False Positive"},
    )
    assert changed.status_code == 201, changed.text
    after_changed = client.get("/actors/A00014", headers=admin_headers).json()
    assert after_changed["confidence_score"] < after_second["confidence_score"]
    assert after_changed["priority_score"] < after_second["priority_score"]
