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

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": "redis",
    "CACHE_REDIS_PORT": 6379,
    "CACHE_REDIS_DB": 1,
}

DATA_CACHE_CONFIG = CACHE_CONFIG

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
# the Public role should be able to view. Currently just the Story 1
# shelter-cost chart's dataset; add a name here (exactly matching Superset's
# own PV naming) whenever another chart/dashboard needs to be public.
PUBLIC_DATASOURCE_NAMES = [
    "[Windsor Housing Data].[windsor_shelter_cost_long](id:1)",
]


def FLASK_APP_MUTATOR(app):
    """Grants the Public role can_read on Chart/Dashboard/Dataset plus
    datasource_access on each name in PUBLIC_DATASOURCE_NAMES. Runs on every
    app startup; safe to re-run -- add_permission_role() is a no-op if the
    role already has that permission (verified: ran this grant twice against
    a live instance, permission list was identical both times, no
    duplicates).

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
