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
