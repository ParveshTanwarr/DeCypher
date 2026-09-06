"""
NLP stylometry service regression tests: posts.csv is keyed by
handle_id, not a "handle"/"author" column, so the compare() lookup used
to always report "insufficient sample text" for real handle names.
"""


def test_compare_known_handles_finds_real_text(client, admin_headers):
    r = client.post(
        "/nlp/compare",
        headers=admin_headers,
        json={"handle_a": "nyxinhex99", "handle_b": "vexatrace"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "error" not in body.get("details", {})
    assert body["similarity_score"] > 0


def test_compare_unknown_handle_reports_insufficient_text(client, admin_headers):
    r = client.post(
        "/nlp/compare",
        headers=admin_headers,
        json={"handle_a": "nyxinhex99", "handle_b": "definitely_not_a_real_handle_xyz"},
    )
    # The router turns a "not enough sample text" result into a 400 with
    # the reason in `detail` -- it doesn't return 200 with an error field.
    assert r.status_code == 400
    assert "insufficient" in r.json()["detail"].lower()
