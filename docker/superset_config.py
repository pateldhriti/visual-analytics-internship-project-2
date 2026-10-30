"""
Superset configuration for the Windsor Housing Analytics project.

Loaded by the Superset container via SUPERSET_CONFIG_PATH. All secrets come
from environment variables (set in .env, never committed) -- nothing
sensitive is hardcoded here.
"""

import os

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

# Embedded SDK spike (docs/embedding_spike.md) -- enables the guest-token
# endpoint and embedDashboard()'s iframe. GUEST_TOKEN_JWT_SECRET signs those
# tokens; must be a real secret (see .env.example), not left at Superset's
# own unsafe default.
FEATURE_FLAGS = {"EMBEDDED_SUPERSET": True}
GUEST_TOKEN_JWT_SECRET = os.environ["GUEST_TOKEN_JWT_SECRET"]

SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@postgres:5432/{os.environ['SUPERSET_METADATA_DB']}"
)

# Public-role dashboard embedding (docs/superset_embedding_research.md's
# Option A) needs a second, separate fix beyond the Public role's own
# permissions (see FLASK_APP_MUTATOR below): Superset's default security
# headers (Flask-Talisman) send `X-Frame-Options: SAMEORIGIN` and a CSP
# with no `frame-ancestors` directive -- verified directly from Superset's
# own default TALISMAN_CONFIG (`python -c "from superset.config import
# TALISMAN_CONFIG"` inside the running container). That blocks ANY
# cross-origin iframe, independent of whether the viewer is authenticated
# or what they're permitted to read -- the browser refuses to render the
# frame before a single request is even sent, which is what showed up as
# "localhost refused to connect" rather than a permission error. This
# re-declares Superset's exact default CSP (same values, not guessed) and
# adds `frame-ancestors` for the dev frontend's origin, plus sets
# `frame_options: None` so the legacy X-Frame-Options header doesn't
# re-block framing in a browser that ignores frame-ancestors. Update
# FRONTEND_ORIGINS below once a real hosting origin exists
# (docs/hosting_decision.md) -- this list is dev-only right now.
FRONTEND_ORIGINS = ["http://localhost:5173"]

TALISMAN_ENABLED = True
TALISMAN_CONFIG = {
    "content_security_policy": {
        "base-uri": ["'self'"],
        "default-src": ["'self'"],
        "img-src": ["'self'", "blob:", "data:"],
        "worker-src": ["'self'", "blob:"],
        "connect-src": ["'self'", "https://api.mapbox.com", "https://events.mapbox.com"],
        "object-src": "'none'",
        "style-src": ["'self'", "'unsafe-inline'"],
        "script-src": ["'self'", "'strict-dynamic'"],
        "frame-ancestors": ["'self'", *FRONTEND_ORIGINS],
    },
    "content_security_policy_nonce_in": ["script-src"],
    "force_https": False,
    "session_cookie_secure": False,
    "frame_options": None,
}

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": "redis",
    "CACHE_REDIS_PORT": 6379,
    "CACHE_REDIS_DB": 1,
}

DATA_CACHE_CONFIG = CACHE_CONFIG

# Real gap found while reviewing this file for hosted reliability: only
# the metadata/chart-data cache above was Redis-backed. Superset's
# dashboard native-filter state and the Explore page's form-data draft
# state each have their OWN cache config, and both default to
# SimpleCache (in-process memory) when not set explicitly -- confirmed
# directly from Superset's own default config, not assumed. In-process
# memory doesn't survive a container restart and isn't shared across
# multiple gunicorn workers, so with more than 1 worker (see
# docker/docker-compose.yml's gunicorn command below), a user's filter
# selection on this project's many native filters (Zone, Tenure,
# Dwelling Scope, etc.) could silently vanish depending on which worker
# handled the next request. Separate Redis DB indices (2, 3) from the
# main cache's DB 1, so clearing one doesn't clear the others.
FILTER_STATE_CACHE_CONFIG = {
    **CACHE_CONFIG,
    "CACHE_REDIS_DB": 2,
}

EXPLORE_FORM_DATA_CACHE_CONFIG = {
    **CACHE_CONFIG,
    "CACHE_REDIS_DB": 3,
}

# Superset's own docs call out that the default webserver timeout (60s)
# can cut off a dashboard's slower charts before they finish rendering.
# This project's heaviest query (v_dashboard1_cma_benchmark's RANK() OVER
# + grouped-median CTEs) runs well under that locally, but a hosted VM
# with less CPU/memory than this dev machine could push it closer -- set
# explicitly rather than left at the default and hoped to be enough.
SUPERSET_WEBSERVER_TIMEOUT = 120

# Public role + anonymous viewing, for embedding charts/dashboards on the
# React site without requiring a login.
#
# PUBLIC_ROLE_LIKE_GAMMA copies Gamma's base permission set (can_read on
# Chart/Dashboard/Dataset list screens, etc.) onto the Public role -- the
# role Superset auto-assigns to any unauthenticated request. This alone
# does NOT grant access to any actual data: Gamma (and so Public) starts
# with zero `datasource_access` grants by design, the same secure-by-
# default model Gamma itself uses. Each dataset that should be publicly
# viewable needs its own explicit grant, added in PUBLIC_DATASOURCE_NAMES
# below -- nothing is public unless listed here.
PUBLIC_ROLE_LIKE_GAMMA = True

# Dataset names (as Superset's own `view_menu.name` on their
# datasource_access permission -- "[<database_name>].[<table>](id:N)") that
# the Public role should be able to view. Add a name here (exactly matching
# Superset's own PV naming -- verified directly against ab_view_menu, not
# guessed from the pattern) whenever another chart/dashboard needs to be
# public. Story 1's dashboard (id 3) uses all 4 of these: the original
# shelter-cost chart's dataset plus the 3 v_story1_* warehouse views its
# other 5 charts were rebuilt on -- found via `dashboard/3/charts`, those 3
# were missing from this list even though the dashboard itself is
# published, so an anonymous viewer would have seen 3 of 6 charts blank.
PUBLIC_DATASOURCE_NAMES = [
    "[Windsor Housing Data].[windsor_shelter_cost_long](id:1)",
    "[Windsor Housing Data].[v_story1_burden_by_tenure](id:5)",
    "[Windsor Housing Data].[v_story1_burden_by_income_band](id:7)",
    "[Windsor Housing Data].[v_story1_burden_by_household_type](id:8)",
    "[Windsor Housing Data].[v_story1_burden_severity](id:15)",
    # Story 1's severity-breakdown chart (chart 32) -- added to dashboard 3
    # after this list was written and never granted, so the React Story 1
    # page (which embeds dashboard 3 anonymously) showed it as an error:
    # GET /api/v1/chart/32/data/ returned 404 for an anonymous request
    # while chart 2 on the same dashboard returned 200.
    "[Windsor Housing Data].[v_story1_burden_severity_breakdown](id:18)",
    # Story 2's dashboard (id TBD) -- added proactively alongside the
    # dashboard build itself, not after an embed exposed a gap this time.
    "[Windsor Housing Data].[v_story2_rent_yoy_change](id:9)",
    "[Windsor Housing Data].[v_story2_rent_growth](id:10)",
    "[Windsor Housing Data].[v_story2_vacancy_trend](id:6)",
    "[Windsor Housing Data].[v_story2_turnover_by_bedroom](id:11)",
    "[Windsor Housing Data].[v_story2_rent_by_zone_bedroom](id:14)",
    # Dashboard 3's zone-level section (etl/build_story2_dashboard.py).
    "[Windsor Housing Data].[v_story2_zone_snapshot](id:19)",
    "[Windsor Housing Data].[v_story2_vacancy_by_zone_trend](id:20)",
    # Dashboard 1 (Windsor Housing Executive Overview) -- Housing Supply
    # section reuses the already-public Story 3 dataset, plus 2 new
    # dashboard-1-only views for the Rental Market YoY and CMA Benchmark
    # tables.
    "[Windsor Housing Data].[v_story3_starts_completions_by_dwelling_type](id:12)",
    # Story 3's dashboard (etl/build_story3_dashboard.py) -- Windsor CMA
    # supply from StatCan 34-10-0154-01.
    "[Windsor Housing Data].[v_story3_windsor_supply_annual](id:21)",
    "[Windsor Housing Data].[v_story3_windsor_supply_per_1000_households](id:22)",
    "[Windsor Housing Data].[v_dashboard1_rental_yoy](id:16)",
    "[Windsor Housing Data].[v_dashboard1_cma_benchmark](id:17)",
]


def FLASK_APP_MUTATOR(app):
    """Grants the Public role can_read on Chart/Dashboard/Dataset plus
    datasource_access on each name in PUBLIC_DATASOURCE_NAMES. Runs on every
    app startup; safe to re-run -- add_permission_role() is a no-op if the
    role already has that permission (verified: ran this grant twice against
    a live instance, permission list was identical both times, no
    duplicates).

    PUBLIC_ROLE_LIKE_GAMMA does NOT actually copy everything Gamma has --
    verified directly against a live instance (ab_permission_view_role):
    Public ended up with only 3 base REST-API permissions (can_read on
    Chart/Dashboard/Dataset), while Gamma has 24 dashboard/explore-related
    ones, including `can_dashboard` on view `Superset` -- the specific
    permission the legacy `/superset/dashboard/<id>/` page route checks.
    Without it, an anonymous visitor hits that route and gets redirected to
    /login, even with every dataset's datasource_access already granted --
    confirmed by curling the dashboard URL anonymously and watching it
    307/302 to /login before this list existed. The extra permissions below
    close that gap so the plain-iframe "Public dashboards" approach
    (docs/superset_embedding_research.md's Option A) actually works for the
    full interactive dashboard page, not just raw chart-data API calls.

    PUBLIC_ROLE_LIKE_GAMMA (above) only syncs Gamma's base permissions, not
    per-dataset access -- this is the piece that does the per-dataset grant,
    since there's no REST API for it and the alternative (editing Superset's
    FAB tables by hand through the UI on every fresh environment) isn't
    repeatable.
    """
    with app.app_context():
        from superset import security_manager as sm
        from superset.extensions import db

        public_role = sm.find_role("Public")
        if public_role is None:
            return

        for perm_name, view_name in [
            ("can_read", "Chart"),
            ("can_read", "Dashboard"),
            ("can_read", "Dataset"),
            ("can_dashboard", "Superset"),
            ("can_explore_json", "Superset"),
            ("can_fetch_datasource_metadata", "Superset"),
            ("can_read", "DashboardFilterStateRestApi"),
            ("can_write", "DashboardFilterStateRestApi"),
        ]:
            pv = sm.find_permission_view_menu(perm_name, view_name)
            if pv is not None:
                sm.add_permission_role(public_role, pv)

        pv_model = sm.permissionview_model
        for datasource_name in PUBLIC_DATASOURCE_NAMES:
            pv = (
                sm.get_session.query(pv_model)
                .join(pv_model.permission)
                .join(pv_model.view_menu)
                .filter_by(name=datasource_name)
                .first()
            )
            if pv is not None:
                sm.add_permission_role(public_role, pv)

        db.session.commit()

# One shared colour palette for the whole project, selectable in any
# chart's "Color Scheme" dropdown. 8-slot CVD-safe categorical palette
# from the dataviz skill's validated reference instance
# (references/palette.md) -- the same source the existing Owner/Renter
# shelter-cost chart's label_colors already use (slots 1-2: blue/orange),
# so picking this scheme for a new chart stays consistent with that one
# rather than introducing a second, uncoordinated set of hues.
#
# Slot order is the CVD-safety mechanism, not cosmetic (see palette.md) --
# do not reorder without re-running the validator. For the Story 4 market
# comparison (Windsor + 4 comparator CMAs -- see
# docs/comparator_cmas_justification.md), markets are assigned in slot
# order: Windsor CMA = slot 1 (blue), Hamilton CMA = slot 2 (orange),
# Kitchener-Cambridge-Waterloo CMA = slot 3 (aqua), London CMA = slot 4
# (yellow), St. Catharines-Niagara CMA = slot 5 (magenta). The original 4
# slots (1-4) were validated against the all-pairs CVD floor needed for
# scatter/bubble/choropleth forms, not just the adjacent-pair floor
# bar/line charts need; slot 5 was added later for the comparator set's
# 5th market and has only the adjacent-pair guarantee the sequential
# palette gives by construction -- re-run the dataviz skill's validator
# with all 5 slots before using this scheme on a scatter/bubble/
# choropleth chart specifically.
EXTRA_CATEGORICAL_COLOR_SCHEMES = [
    {
        "id": "windsor_housing",
        "label": "Windsor Housing Analytics",
        "description": (
            "Validated CVD-safe categorical palette for this project "
            "(dataviz skill references/palette.md). Slot order matters -- "
            "see this file's comment above for the Story 4 market assignment."
        ),
        "colors": [
            "#2a78d6",  # slot 1 blue
            "#eb6834",  # slot 2 orange
            "#1baf7a",  # slot 3 aqua
            "#eda100",  # slot 4 yellow
            "#e87ba4",  # slot 5 magenta
            "#008300",  # slot 6 green
            "#4a3aa7",  # slot 7 violet
            "#e34948",  # slot 8 red
        ],
    }
]
