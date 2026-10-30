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


def test_known_dashboard_returns_token_and_uuid():
    client = FakeClient()
    status, body = server.issue_token(client, "story1")
    assert status == 200
    assert body["dashboardUuid"] == "uuid-3"
    assert body["token"] == "token-for-uuid-3"
    assert client.requested_ids == [3]


@pytest.mark.parametrize("name", ["story4", "", None, "3", 3])
def test_unknown_dashboard_is_rejected_without_calling_superset(name):
    client = FakeClient()
    status, body = server.issue_token(client, name)
    assert status == 404
    assert body["allowed"] == ["story1"]
    assert client.requested_ids == []


@pytest.mark.parametrize(
    "error", [server.SupersetError("embedding not enabled"), requests.ConnectionError("refused")]
)
def test_superset_failure_maps_to_502(error):
    status, body = server.issue_token(FakeClient(fail_with=error), "story1")
    assert status == 502
    assert "token" not in body


@pytest.fixture
def running_server():
    server.GuestTokenHandler.client = FakeClient()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.GuestTokenHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def post(url, data: bytes):
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.headers, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, err.headers, json.loads(err.read())


def test_http_token_response_is_not_cacheable(running_server):
    status, headers, body = post(f"{running_server}/api/guest-token", b'{"dashboard": "story1"}')
    assert status == 200
    assert headers["Cache-Control"] == "no-store"
    assert body["dashboardUuid"] == "uuid-3"


@pytest.mark.parametrize("payload", [b"not json", b"[1, 2]"])
def test_http_rejects_malformed_body(running_server, payload):
    status, _, body = post(f"{running_server}/api/guest-token", payload)
    assert status == 400
    assert "error" in body


def test_http_unknown_path_is_404(running_server):
    status, _, _ = post(f"{running_server}/api/other", b"{}")
    assert status == 404


def test_http_health(running_server):
    with urllib.request.urlopen(f"{running_server}/api/health") as resp:
        assert json.loads(resp.read()) == {"status": "ok"}
