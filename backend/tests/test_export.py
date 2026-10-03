"""Export authorization regression tests."""


def test_investigator_role_can_export(client, analyst_headers):
    r = client.get("/export/json", headers=analyst_headers)
    assert r.status_code == 200
    assert len(r.json()) > 0

def test_investigator_can_export_pdf(client, analyst_headers):
    r = client.get("/export/report", headers=analyst_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")


def test_admin_role_can_export(client, admin_headers):
    r = client.get("/export/json", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) > 0


def test_admin_can_export_csv(client, admin_headers):
    r = client.get("/export/csv", headers=admin_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")


def test_investigator_can_export_actor_formats(client, analyst_headers):
    actor_id = "A00001"

    json_response = client.get(
        f"/export/actor/{actor_id}/json",
        headers=analyst_headers,
    )
    assert json_response.status_code == 200
    payload = json_response.json()
    assert payload["actor_id"] == actor_id
    assert "priority_score" in payload
    assert "graph_priority_score" in payload
    assert "observations" in payload

    csv_response = client.get(
        f"/export/actor/{actor_id}/csv",
        headers=analyst_headers,
    )
    assert csv_response.status_code == 200
    assert "graph_priority_score" in csv_response.text

    pdf_response = client.get(
        f"/export/actor/{actor_id}/report",
        headers=analyst_headers,
    )
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"].startswith("application/pdf")


def test_correlation_get_is_side_effect_free_and_refresh_persists(
    client, admin_headers
):
    response = client.get(
        "/correlation/actor/A00001",
        headers=admin_headers,
        params={"handle_a": "nyxinhex99", "handle_b": "vexatrace"},
    )
    assert response.status_code == 200
    correlation = response.json()

    persisted_before = client.get("/actors/A00001", headers=admin_headers)
    assert persisted_before.status_code == 200
    before_payload = persisted_before.json()

    read_again = client.get("/actors/A00001", headers=admin_headers)
    assert read_again.status_code == 200
    assert read_again.json()["confidence_score"] == before_payload["confidence_score"]
    assert read_again.json()["priority_score"] == before_payload["priority_score"]

    refresh = client.post(
        "/correlation/actor/A00001/refresh",
        headers=admin_headers,
        params={"handle_a": "nyxinhex99", "handle_b": "vexatrace"},
    )
    assert refresh.status_code == 200, refresh.text
    correlation = refresh.json()

    actor = client.get("/actors/A00001", headers=admin_headers)
    assert actor.status_code == 200
    actor_payload = actor.json()

    assert abs(
        float(actor_payload["confidence_score"]) -
        float(correlation["overall_confidence"])
    ) < 1e-4
    assert actor_payload["priority_score"] == correlation["priority"]["score"]
