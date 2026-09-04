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
