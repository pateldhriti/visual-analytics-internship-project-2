"""
Guest-token endpoint for embedding Superset dashboards in the React site
with the Embedded SDK -- the missing backend docs/embedding_spike.md
identified ("this project has no backend server to mint guest tokens
from").

    POST /api/guest-token   {"dashboard": "story1"}
        -> 200 {"token": "...", "dashboardUuid": "...", "supersetDomain": "..."}
    GET  /api/health        -> 200 {"status": "ok"}

Why a server at all: minting a guest token needs an admin-level Superset
login (`can_grant_guest_token`), which must never ship to the browser.
This process holds that login and hands the browser only a short-lived
token scoped to one dashboard.

Only dashboards listed in EMBEDDABLE_DASHBOARDS can be requested, by a
short name rather than a Superset id, so a caller can't ask for a token
to an arbitrary dashboard. Each must first have embedding enabled in
Superset (etl/enable_dashboard_embedding.py), which is where its UUID comes
from; the UUID is looked up here, not hardcoded in the frontend.

Hardening (each check answers before Superset is contacted):
  - Origin: the request's Origin header (or, if absent, its Referer) must
    be one of the site's own origins (FRONTEND_ORIGINS in .env). Blocks
    other websites from minting tokens through a visitor's browser. -> 403
  - Content type: the body must be application/json, so a cross-site HTML
    form cannot post to it without a CORS preflight, which this server
    never approves. -> 415
  - Size: bodies over MAX_BODY_BYTES are refused unread. -> 413
  - Rate limit: RATE_LIMIT_REQUESTS per client per RATE_LIMIT_WINDOW
    seconds (a page needs one token per dashboard plus a refresh every few
    minutes). -> 429 with Retry-After
  - It still listens on 127.0.0.1 only; in production the site's reverse
    proxy forwards /api to it (docker/Caddyfile).

Python standard library HTTP server plus `requests` -- no web framework,
since this is one endpoint. Single-process and meant for local
development and the prototype; for production it would sit behind the
same reverse proxy as the site.

Requires .env with SUPERSET_ADMIN_USER / SUPERSET_ADMIN_PASSWORD (see
.env.example) and Superset running. The Vite dev server proxies /api to
this process (web/vite.config.js), so the browser calls it same-origin.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe api\\guest_token_server.py
"""

import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

SUPERSET_URL = os.environ.get("SUPERSET_URL", "http://localhost:8088")
HOST = os.environ.get("GUEST_TOKEN_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("GUEST_TOKEN_API_PORT", "8090"))
REQUEST_TIMEOUT = 15

# short name the frontend sends -> the dashboard's slug, the fixed URL name its
# builder sets (Superset accepts it wherever it accepts an id; ids differ on
# every Superset, so the same API works against ours and the university's)
EMBEDDABLE_DASHBOARDS = {
    "story1": "windsor-story-1",  # Story 1: Who faces the greatest affordability pressure?
    "story2": "windsor-story-2",  # Story 2: What is happening in Windsor's rental market?
    "story3": "windsor-story-3",  # Story 3: Is Windsor building enough housing?
    "story4": "windsor-story-4",  # Story 4: How does Windsor compare to similar markets?
    "story5": "windsor-story-5",  # Story 5: How do affordability, rental conditions, and supply fit together?
}

# The site's own origins (same variable superset_config.py reads).
ALLOWED_ORIGINS = {
    origin.strip().rstrip("/")
    for origin in os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
}
MAX_BODY_BYTES = 1024
RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW = 60  # seconds
TRUSTED_PROXIES = {"127.0.0.1", "::1"}

# The guest user Superset records for embedded views. Not a real account --
# guest tokens carry their own identity and get the Public role's
# permissions (Superset's GUEST_ROLE_NAME default).
GUEST_USER = {"username": "story-page-viewer", "first_name": "Story", "last_name": "Viewer"}


class SupersetError(Exception):
    pass


class RateLimiter:
    """Sliding-window limit of `limit` requests per `window` seconds per
    client key. In memory: this is a single process."""

    def __init__(self, limit: int, window: float, clock=time.monotonic):
        self.limit = limit
        self.window = window
        self.clock = clock
        self.hits = {}
        self.lock = threading.Lock()

    def check(self, key: str) -> float:
        """0 if allowed (and counted), else the seconds to wait."""
        now = self.clock()
        with self.lock:
            recent = [t for t in self.hits.get(key, []) if now - t < self.window]
            if len(recent) >= self.limit:
                self.hits[key] = recent
                return self.window - (now - recent[0])
            recent.append(now)
            self.hits[key] = recent
            return 0.0


def origin_allowed(headers, allowed=None) -> bool:
    """True if the request comes from one of the site's own pages."""
    allowed = ALLOWED_ORIGINS if allowed is None else allowed
    origin = (headers.get("Origin") or "").rstrip("/")
    if origin:
        return origin in allowed
    referer = headers.get("Referer") or ""
    return any(referer == o or referer.startswith(o + "/") for o in allowed)


class SupersetClient:
    """Admin session against Superset, reused across requests and
    re-established once if Superset rejects it (expired cookie, Superset
    restart). Form login rather than the JWT login endpoint, for the same
    reason as etl/setup_superset_dashboard.py's get_session()."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.session = None
        self.headers = {}
        self.embedded_uuids = {}
        self.lock = threading.Lock()

    def login(self) -> None:
        session = requests.Session()
        page = session.get(f"{self.base_url}/login/", timeout=REQUEST_TIMEOUT)
        page.raise_for_status()
        match = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', page.text)
        if not match:
            raise SupersetError("Superset login page has no CSRF token")

        resp = session.post(
            f"{self.base_url}/login/",
            data={"username": self.username, "password": self.password, "csrf_token": match.group(1)},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()

        csrf = session.get(f"{self.base_url}/api/v1/security/csrf_token/", timeout=REQUEST_TIMEOUT)
        if csrf.status_code != 200:
            raise SupersetError(f"Superset login failed (csrf_token returned {csrf.status_code})")

        self.session = session
        self.headers = {"X-CSRFToken": csrf.json()["result"], "Referer": self.base_url}

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        with self.lock:
            if self.session is None:
                self.login()
            resp = self.session.request(
                method, f"{self.base_url}{path}", headers=self.headers, timeout=REQUEST_TIMEOUT, **kwargs
            )
            if resp.status_code in (401, 403):
                self.login()
                resp = self.session.request(
                    method, f"{self.base_url}{path}", headers=self.headers, timeout=REQUEST_TIMEOUT, **kwargs
                )
        return resp

    def embedded_uuid(self, dashboard_id: int | str) -> str:
        if dashboard_id not in self.embedded_uuids:
            resp = self.request("GET", f"/api/v1/dashboard/{dashboard_id}/embedded")
            if resp.status_code == 404:
                raise SupersetError(
                    f"Embedding is not enabled for dashboard {dashboard_id} -- run etl/enable_dashboard_embedding.py"
                )
            resp.raise_for_status()
            self.embedded_uuids[dashboard_id] = resp.json()["result"]["uuid"]
        return self.embedded_uuids[dashboard_id]

    def guest_token(self, embedded_uuid: str) -> str:
        resp = self.request(
            "POST",
            "/api/v1/security/guest_token/",
            json={
                "user": GUEST_USER,
                "resources": [{"type": "dashboard", "id": embedded_uuid}],
                # No row-level security: every dataset on this site is public.
                "rls": [],
            },
        )
        if resp.status_code != 200:
            raise SupersetError(f"guest_token returned {resp.status_code}: {resp.text[:200]}")
        return resp.json()["token"]


def issue_token(client: SupersetClient, dashboard_name) -> tuple[int, dict]:
    """Returns (HTTP status, JSON body). Kept separate from the HTTP
    handler so the allowlist and error mapping can be tested without a
    socket."""
    dashboard_id = EMBEDDABLE_DASHBOARDS.get(dashboard_name)
    if dashboard_id is None:
        return 404, {"error": f"Unknown dashboard {dashboard_name!r}", "allowed": sorted(EMBEDDABLE_DASHBOARDS)}
    try:
        embedded_uuid = client.embedded_uuid(dashboard_id)
        token = client.guest_token(embedded_uuid)
    except (SupersetError, requests.RequestException) as exc:
        return 502, {"error": f"Could not get a guest token from Superset: {exc}"}
    return 200, {"token": token, "dashboardUuid": embedded_uuid, "supersetDomain": SUPERSET_URL}


class GuestTokenHandler(BaseHTTPRequestHandler):
    client: SupersetClient = None  # set in main()
    limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW)

    def send_json(self, status: int, body: dict, extra_headers: dict | None = None) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        # Tokens are short-lived and per-request; never let a proxy cache one.
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

    def client_key(self) -> str:
        """The caller's address; behind a local reverse proxy, the first
        X-Forwarded-For address it reports."""
        peer = self.client_address[0]
        forwarded = self.headers.get("X-Forwarded-For")
        if peer in TRUSTED_PROXIES and forwarded:
            return forwarded.split(",")[0].strip()
        return peer

    def do_GET(self):
        if self.path == "/api/health":
            self.send_json(200, {"status": "ok"})
        else:
            self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/api/guest-token":
            self.send_json(404, {"error": "Not found"})
            return
        if not origin_allowed(self.headers):
            self.send_json(403, {"error": "Requests must come from the site's own pages"})
            return
        content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if content_type != "application/json":
            self.send_json(415, {"error": "Body must be sent as application/json"})
            return
        try:
            declared = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            declared = MAX_BODY_BYTES + 1
        if declared > MAX_BODY_BYTES:
            self.send_json(413, {"error": f"Body larger than {MAX_BODY_BYTES} bytes"})
            return
        wait = self.limiter.check(self.client_key())
        if wait:
            self.send_json(
                429,
                {"error": "Too many token requests; try again shortly"},
                {"Retry-After": str(max(1, int(wait + 0.999)))},
            )
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
        except (ValueError, json.JSONDecodeError):
            self.send_json(400, {"error": "Body must be JSON"})
            return
        if not isinstance(body, dict):
            self.send_json(400, {"error": "Body must be a JSON object"})
            return
        status, payload = issue_token(self.client, body.get("dashboard"))
        self.send_json(status, payload)


def main() -> None:
    GuestTokenHandler.client = SupersetClient(
        SUPERSET_URL, os.environ["SUPERSET_ADMIN_USER"], os.environ["SUPERSET_ADMIN_PASSWORD"]
    )
    server = ThreadingHTTPServer((HOST, PORT), GuestTokenHandler)
    print(f"Guest-token API on http://{HOST}:{PORT} (Superset: {SUPERSET_URL})")
    print(f"Embeddable dashboards: {', '.join(sorted(EMBEDDABLE_DASHBOARDS))}")
    print(f"Allowed origins: {', '.join(sorted(ALLOWED_ORIGINS))}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
