"""
Enable Embedded SDK access for the five story dashboards, so the
guest-token API (api/guest_token_server.py) can issue tokens for them and
the React story pages can embed them with embedDashboard().

POST /api/v1/dashboard/<id>/embedded creates a dashboard's embedded
configuration, or updates it if one already exists, keeping the same
UUID -- so this is safe to re-run, e.g. after adding an origin to
FRONTEND_ORIGINS in .env. allowed_domains is the list of sites Superset
lets frame the embedded dashboard; it must match the frontend's origin
exactly (scheme, host and port), the same origins docker/superset_config.py
adds to the CSP frame-ancestors and the guest-token API accepts.

Requires Superset running and .env with SUPERSET_ADMIN_USER /
SUPERSET_ADMIN_PASSWORD (see .env.example).

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\enable_dashboard_embedding.py
"""

import os

from setup_superset_dashboard import SUPERSET_URL, get_session

# Same ids as api/guest_token_server.py's EMBEDDABLE_DASHBOARDS.
DASHBOARDS = {
    3: "Story 1: Who faces the greatest affordability pressure?",
    4: "Story 2: What is happening in Windsor's rental market?",
    7: "Story 3: Is Windsor building enough housing?",
    6: "Story 4: How does Windsor compare to similar markets?",
    8: "Story 5: How do affordability, rental conditions, and supply fit together?",
}
DEFAULT_ORIGINS = "http://localhost:5173"


def allowed_domains() -> list[str]:
    """FRONTEND_ORIGINS from .env (comma-separated). Read after
    get_session(), which loads .env."""
    return [
        origin.strip()
        for origin in os.environ.get("FRONTEND_ORIGINS", DEFAULT_ORIGINS).split(",")
        if origin.strip()
    ]


def enable(session, headers, dashboard_id: int) -> str:
    resp = session.post(
        f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}/embedded",
        headers=headers,
        json={"allowed_domains": allowed_domains()},
    )
    resp.raise_for_status()
    return resp.json()["result"]["uuid"]


def main(dashboard_ids=None) -> dict:
    session, headers = get_session()
    uuids = {}
    for dashboard_id in dashboard_ids or DASHBOARDS:
        uuids[dashboard_id] = enable(session, headers, dashboard_id)
        print(f"Embedding enabled for dashboard {dashboard_id} ({DASHBOARDS.get(dashboard_id, '')}): uuid={uuids[dashboard_id]}")
    print(f"  allowed domains: {', '.join(allowed_domains())}")
    return uuids


if __name__ == "__main__":
    main()
