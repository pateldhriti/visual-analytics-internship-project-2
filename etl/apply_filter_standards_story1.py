"""
Apply docs/filter_standards.md's naming rule to Story 1's dashboard
(id=3), as that doc's worked example: rename the "Household type"
native filter to "Household Type" -- Title Case, matching every other
word in the project's other filter names (Tenure, Zone, Dwelling
Scope). Placement (Tenure first) and scope (hardcoded-tenure KPI tiles
already excluded, per etl/fix_story1_tenure_filter_scope.py) already
match the standard, so this script only touches the name.

Requires Superset running and a .env file with SUPERSET_ADMIN_USER/
SUPERSET_ADMIN_PASSWORD (see .env.example).

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\apply_filter_standards_story1.py
"""

import json

from setup_superset_dashboard import SUPERSET_URL, get_session

DASHBOARD_ID = 3
RENAMES = {"Household type": "Household Type"}


def main():
    session, headers = get_session()
    print("Logged in to Superset.")

    resp = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{DASHBOARD_ID}", headers=headers)
    resp.raise_for_status()
    metadata = json.loads(resp.json()["result"]["json_metadata"])

    changed = False
    for f in metadata.get("native_filter_configuration", []):
        if f["name"] in RENAMES:
            new_name = RENAMES[f["name"]]
            print(f"'{f['name']}' -> '{new_name}'")
            f["name"] = new_name
            changed = True

    if not changed:
        print("No change needed -- filter names already match the standard.")
        return

    resp = session.put(
        f"{SUPERSET_URL}/api/v1/dashboard/{DASHBOARD_ID}",
        headers=headers,
        json={"json_metadata": json.dumps(metadata)},
    )
    resp.raise_for_status()
    print(f"Dashboard {DASHBOARD_ID} updated.")


if __name__ == "__main__":
    main()
