"""
Enable Embedded SDK access for Story 1's dashboard (id 3) only.

Kept for existing instructions that name this script; the general version
is etl/enable_dashboard_embedding.py, which enables all four story
dashboards with the same settings.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\enable_story1_embedding.py
"""

from enable_dashboard_embedding import main as enable_dashboards

DASHBOARD_ID = 3  # Story 1: Who faces the greatest affordability pressure?


def main() -> str:
    return enable_dashboards([DASHBOARD_ID])[DASHBOARD_ID]


if __name__ == "__main__":
    main()
