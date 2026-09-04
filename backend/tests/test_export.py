"""Export is admin-only -- role authorization regression tests."""


def test_investigator_role_cannot_export(client, analyst_headers):
    r = client.get("/export/json", headers=analyst_headers)
    assert r.status_code == 403


def test_admin_role_can_export(client, admin_headers):
    r = client.get("/export/json", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) > 0


def test_admin_can_export_csv(client, admin_headers):
    r = client.get("/export/csv", headers=admin_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
