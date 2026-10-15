"""
Superset configuration for the Windsor Housing Analytics project.

Loaded by the Superset container via SUPERSET_CONFIG_PATH. All secrets come
from environment variables (set in .env, never committed) -- nothing
sensitive is hardcoded here.
"""

import os

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

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
# comparison (Windsor + 3 comparator CMAs), markets are assigned in slot
# order: Windsor CMA = slot 1 (blue), London CMA = slot 2 (orange),
# Kitchener-Cambridge-Waterloo CMA = slot 3 (aqua), Toronto CMA = slot 4
# (yellow) -- the first 4 slots clear the all-pairs CVD floor for
# scatter/bubble/choropleth forms, not just the adjacent-pair floor bar/
# line charts need, so this ordering is safe for any Story 4 chart type.
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
