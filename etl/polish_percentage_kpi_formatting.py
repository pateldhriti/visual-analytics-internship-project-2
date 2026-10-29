"""
Standardize percentage formatting across Dashboard 1 (Executive
Overview) and Dashboard 2 (Story 1 / Affordability) charts that have no
idempotent builder script of their own -- Renter/Owner Burden Rate
(chart ids 3, 4, shared by both dashboards) and Burden Rate by Income
Band / Household Type (6, 7).

Real inconsistency found while reviewing both dashboards for visual
consistency: every one of these charts stores its column already
multiplied by 100 (e.g. burden_rate_pct = 34.8, not 0.348) and used
y_axis_format ".1f" -- which d3-format renders as a bare "34.8", no "%"
sign at all. The one chart that DOES show a "%" on these same
dashboards (chart 2, "Share of households... by tenure") works because
its own SQL metric computes a 0-1 fraction and uses format ".1%"
instead -- confirmed directly by reading each chart's live params, not
assumed. This fixes charts 3/4/6/7 the same way chart 2 already works:
divide by 100 in the metric expression, format ".1%". (Charts 14/15/17/19,
which DO have an idempotent builder, are fixed at the source in
etl/finalize_story1_layout.py and etl/build_dashboard1_overview.py
instead of here.)

Requires Superset running and a .env file with SUPERSET_ADMIN_USER/
SUPERSET_ADMIN_PASSWORD (see .env.example).

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\polish_percentage_kpi_formatting.py
"""

import json

from setup_superset_dashboard import SUPERSET_URL, get_session

# chart id -> (source column, metric label)
PERCENTAGE_CHARTS = {
    3: ("burden_rate_pct", "Renter Burden Rate"),
    4: ("burden_rate_pct", "Owner Burden Rate"),
    6: ("burden_rate_pct", "Burden Rate (%)"),
    7: ("burden_rate_pct", "Burden Rate (%)"),
}


def fixed_metric(column: str, label: str) -> dict:
    return {
        "expressionType": "SQL",
        "sqlExpression": f"MAX({column}) / 100.0",
        "label": label,
    }


def main():
    session, headers = get_session()
    print("Logged in to Superset.")

    for chart_id, (column, label) in PERCENTAGE_CHARTS.items():
        resp = session.get(f"{SUPERSET_URL}/api/v1/chart/{chart_id}", headers=headers)
        resp.raise_for_status()
        res = resp.json()["result"]
        params = json.loads(res["params"])

        if params.get("y_axis_format") == ".1%":
            print(f"Chart {chart_id} ({res['slice_name']}): already fixed, skipping.")
            continue

        new_metric = fixed_metric(column, label)
        if "metric" in params:
            params["metric"] = new_metric
        else:
            params["metrics"] = [new_metric]
        params["y_axis_format"] = ".1%"

        put_resp = session.put(
            f"{SUPERSET_URL}/api/v1/chart/{chart_id}",
            headers=headers,
            json={"params": json.dumps(params)},
        )
        put_resp.raise_for_status()
        print(f"Chart {chart_id} ({res['slice_name']}): metric -> SQL /100.0, format -> .1%")


if __name__ == "__main__":
    main()
