"""
Auth regression tests. Covers the bug where the "analyst" demo account's
placeholder bcrypt hash made login impossible, plus the auth-enforcement
and rate-limiting gaps found afterward.
"""


def test_analyst_login_succeeds(client):
    r = client.post("/auth/token", data={"username": "analyst", "password": "analystpassword"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_admin_login_succeeds(client):
    r = client.post("/auth/token", data={"username": "admin", "password": "adminpassword"})
    assert r.status_code == 200


def test_scanner_service_login_succeeds(client):
    r = client.post(
        "/auth/token",
        data={"username": "scanner_service", "password": "scanner_service_devkey_change_me"},
    )
    assert r.status_code == 200


def test_wrong_password_rejected(client):
    r = client.post("/auth/token", data={"username": "analyst", "password": "wrong"})
    assert r.status_code == 401


def test_unknown_user_rejected(client):
    r = client.post("/auth/token", data={"username": "ghost", "password": "whatever"})
    assert r.status_code == 401


def test_protected_route_requires_token(client):
    r = client.get("/actors")
    assert r.status_code == 401


def test_health_check_is_public(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_login_rate_limit_kicks_in(client):
    username = "rate_limit_probe_user"
    statuses = []
    for _ in range(7):
        r = client.post("/auth/token", data={"username": username, "password": "wrong"})
        statuses.append(r.status_code)
    assert 429 in statuses, "expected the login rate limiter to trigger after repeated attempts"
