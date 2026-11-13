"""
Tests for api/guest_token_server.py's request handling, against a fake
Superset client -- no Superset or network needed.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe -m pytest api\\test_guest_token_server.py -v
"""

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest
import requests

import guest_token_server as server

SITE = "http://localhost:5173"  # the default FRONTEND_ORIGINS


class FakeClient:
    def __init__(self, fail_with=None):
        self.fail_with = fail_with
        self.requested_ids = []

    def embedded_uuid(self, dashboard_id):
        self.requested_ids.append(dashboard_id)
        if self.fail_with:
            raise self.fail_with
        return f"uuid-{dashboard_id}"

    def guest_token(self, embedded_uuid):
        return f"token-for-{embedded_uuid}"


@pytest.mark.parametrize("name, dashboard_id", [(f"story{n}", f"windsor-story-{n}") for n in range(1, 6)])
def test_each_story_dashboard_returns_token_and_uuid(name, dashboard_id):
    client = FakeClient()
    status, body = server.issue_token(client, name)
    assert status == 200
    assert body["dashboardUuid"] == f"uuid-{dashboard_id}"
    assert body["token"] == f"token-for-uuid-{dashboard_id}"
    assert client.requested_ids == [dashboard_id]


@pytest.mark.parametrize("name", ["story6", "", None, "8", 8])
def test_unknown_dashboard_is_rejected_without_calling_superset(name):
    client = FakeClient()
    status, body = server.issue_token(client, name)
    assert status == 404
    assert body["allowed"] == ["story1", "story2", "story3", "story4", "story5"]
    assert client.requested_ids == []


@pytest.mark.parametrize(
    "error", [server.SupersetError("embedding not enabled"), requests.ConnectionError("refused")]
)
def test_superset_failure_maps_to_502(error):
    status, body = server.issue_token(FakeClient(fail_with=error), "story1")
    assert status == 502
    assert "token" not in body


@pytest.mark.parametrize(
    "headers, allowed",
    [
        ({"Origin": SITE}, True),
        ({"Origin": SITE + "/"}, True),
        ({"Origin": "https://evil.example"}, False),
        ({"Origin": "http://localhost:5173.evil.example"}, False),
        ({"Referer": SITE + "/stories/rental-market"}, True),
        ({"Referer": "http://localhost:5173.evil.example/x"}, False),
        ({}, False),
    ],
)
def test_origin_check(headers, allowed):
    assert server.origin_allowed(headers, {SITE}) is allowed


def test_rate_limiter_blocks_then_recovers():
    now = [0.0]
    limiter = server.RateLimiter(limit=3, window=60, clock=lambda: now[0])
    assert [limiter.check("a") for _ in range(3)] == [0.0, 0.0, 0.0]
    assert limiter.check("a") == 60  # 4th request inside the window
    assert limiter.check("b") == 0.0  # other clients are unaffected
    now[0] = 61
    assert limiter.check("a") == 0.0  # window has passed


@pytest.fixture
def running_server(monkeypatch):
    server.GuestTokenHandler.client = FakeClient()
    monkeypatch.setattr(server, "ALLOWED_ORIGINS", {SITE})
    monkeypatch.setattr(server.GuestTokenHandler, "limiter", server.RateLimiter(5, 60))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.GuestTokenHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def post(url, data: bytes, headers=None):
    base = {"Content-Type": "application/json", "Origin": SITE}
    base.update(headers or {})
    req = urllib.request.Request(url, data=data, method="POST", headers={k: v for k, v in base.items() if v is not None})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.headers, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, err.headers, json.loads(err.read())


def test_http_token_response_is_not_cacheable(running_server):
    status, headers, body = post(f"{running_server}/api/guest-token", b'{"dashboard": "story1"}')
    assert status == 200
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert body["dashboardUuid"] == "uuid-windsor-story-1"


@pytest.mark.parametrize("payload", [b"not json", b"[1, 2]"])
def test_http_rejects_malformed_body(running_server, payload):
    status, _, body = post(f"{running_server}/api/guest-token", payload)
    assert status == 400
    assert "error" in body


def test_http_rejects_other_origins(running_server):
    status, _, body = post(f"{running_server}/api/guest-token", b'{"dashboard": "story1"}', {"Origin": "https://evil.example"})
    assert status == 403
    assert "token" not in body


def test_http_rejects_missing_origin(running_server):
    status, _, _ = post(f"{running_server}/api/guest-token", b'{"dashboard": "story1"}', {"Origin": None})
    assert status == 403


def test_http_rejects_form_posts(running_server):
    status, _, _ = post(
        f"{running_server}/api/guest-token",
        b"dashboard=story1",
        {"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert status == 415


def test_http_rejects_large_bodies(running_server):
    big = json.dumps({"dashboard": "story1", "pad": "x" * 2000}).encode()
    status, _, _ = post(f"{running_server}/api/guest-token", big)
    assert status == 413


def test_http_rate_limit(running_server):
    statuses = [post(f"{running_server}/api/guest-token", b'{"dashboard": "story2"}')[0] for _ in range(6)]
    assert statuses[:5] == [200] * 5
    status, headers, _ = post(f"{running_server}/api/guest-token", b'{"dashboard": "story2"}')
    assert status == 429
    assert int(headers["Retry-After"]) >= 1


def test_http_unknown_path_is_404(running_server):
    status, _, _ = post(f"{running_server}/api/other", b"{}")
    assert status == 404


def test_http_health(running_server):
    with urllib.request.urlopen(f"{running_server}/api/health") as resp:
        assert json.loads(resp.read()) == {"status": "ok"}


class FakeResponse:
    def __init__(self, status, body):
        self.status_code, self.body = status, body

    def json(self):
        return self.body


class FakeSession:
    """Records requests; answers Superset's REST login and CSRF endpoints."""

    def __init__(self, login_status=200):
        self.headers, self.calls, self.login_status = {}, [], login_status

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs.get("json")))
        return FakeResponse(self.login_status, {"access_token": "jwt"} if self.login_status == 200 else {})

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, None))
        return FakeResponse(200, {"result": "csrf"})


def test_rest_login_for_superset_without_a_login_form(monkeypatch):
    fake = FakeSession()
    monkeypatch.setattr(server.requests, "Session", lambda: fake)
    client = server.SupersetClient("https://superset.example", "user", "pw", provider="ldap")
    client.login()
    method, url, body = fake.calls[0]
    assert (method, url) == ("POST", "https://superset.example/api/v1/security/login")
    assert body["provider"] == "ldap" and body["username"] == "user"
    assert fake.headers["Authorization"] == "Bearer jwt"
    assert not any(u.endswith("/login/") for _, u, _ in fake.calls)  # the form is never used
    assert client.headers["X-CSRFToken"] == "csrf"


def test_rest_login_failure_is_reported(monkeypatch):
    monkeypatch.setattr(server.requests, "Session", lambda: FakeSession(login_status=401))
    client = server.SupersetClient("https://superset.example", "user", "wrong", provider="ldap")
    with pytest.raises(server.SupersetError, match="login failed"):
        client.login()
