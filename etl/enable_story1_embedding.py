"""
Enable Embedded SDK access for Story 1's dashboard (id 3), so the
guest-token API (api/guest_token_server.py) can issue tokens for it and
the React Story 1 page can embed it with embedDashboard().

POST /api/v1/dashboard/<id>/embedded creates the dashboard's embedded
configuration, or updates it if one already exists, keeping the same
UUID -- so this is safe to re-run, e.g. after adding an origin to
ALLOWED_DOMAINS. allowed_domains is the list of sites Superset lets frame
the embedded dashboard; it must match the frontend's origin exactly
(scheme, host and port), the same origin docker/superset_config.py's
FRONTEND_ORIGINS adds to the CSP frame-ancestors.

Requires Superset running and .env with SUPERSET_ADMIN_USER /
SUPERSET_ADMIN_PASSWORD (see .env.example).

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\enable_story1_embedding.py
"""

from setup_superset_dashboard import SUPERSET_URL, get_session

DASHBOARD_ID = 3  # Story 1: Who faces the greatest affordability pressure?
ALLOWED_DOMAINS = ["http://localhost:5173"]


def main() -> str:
    session, headers = get_session()
    resp = session.post(
        f"{SUPERSET_URL}/api/v1/dashboard/{DASHBOARD_ID}/embedded",
        headers=headers,
        json={"allowed_domains": ALLOWED_DOMAINS},
    )
    resp.raise_for_status()
    result = resp.json()["result"]
    print(f"Embedding enabled for dashboard {DASHBOARD_ID}: uuid={result['uuid']}")
    print(f"  allowed domains: {', '.join(result['allowed_domains'])}")
    return result["uuid"]


if __name__ == "__main__":
    main()
