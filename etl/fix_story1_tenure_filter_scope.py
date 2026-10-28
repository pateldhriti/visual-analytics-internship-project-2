"""
Fix a real bug found while validating Story 1's Tenure native filter:
the "Renter Burden Rate" and "Owner Burden Rate" KPI tiles (chart ids 3
and 4) were in scope for both native filters on dashboard 3, even though
each KPI already has its own hardcoded tenure filter baked into its own
params (tenure == 'Renter' / tenure == 'Owner').

Superset ANDs a native filter's selection onto each in-scope chart's own
adhoc_filters. Selecting "Owner" in the Tenure filter would apply
tenure == 'Owner' on top of the Renter KPI's own tenure == 'Renter' --
an impossible AND condition, returning zero rows. The KPI would go
blank instead of staying the fixed, independent figure it's meant to be
-- confirmed directly from the live chart params
(SELECT params FROM slices WHERE id IN (3,4)), not assumed.

Charts 6 and 7 (Burden Rate by Income Band / Household Type) were
checked too: neither dataset exposes a tenure or household_type-named
column that would cause the equivalent conflict, so they're left as-is.

Fix: remove chart ids 3 and 4 from both native filters' chartsInScope --
these two KPI tiles are meant to be fixed, independent summary numbers,
not filtered by anything on this dashboard.

Requires Superset running and a .env file with SUPERSET_ADMIN_USER/
SUPERSET_ADMIN_PASSWORD (see .env.example).

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\fix_story1_tenure_filter_scope.py
"""

import json

from setup_superset_dashboard import SUPERSET_URL, get_session

DASHBOARD_ID = 3
INDEPENDENT_KPI_CHART_IDS = {3, 4}  # Renter Burden Rate, Owner Burden Rate


def main():
    session, headers = get_session()
    print("Logged in to Superset.")

    resp = session.get(f"{SUPERSET_URL}/api/v1/dashboard/{DASHBOARD_ID}", headers=headers)
    resp.raise_for_status()
    metadata = json.loads(resp.json()["result"]["json_metadata"])

    native_filters = metadata.get("native_filter_configuration", [])
    changed = False
    for f in native_filters:
        before = set(f["chartsInScope"])
        after = sorted(before - INDEPENDENT_KPI_CHART_IDS)
        if after != sorted(before):
            print(f"{f['name']}: chartsInScope {sorted(before)} -> {after}")
            f["chartsInScope"] = after
            changed = True

    if not changed:
        print("No change needed -- chart ids 3/4 already out of scope for every filter.")
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
