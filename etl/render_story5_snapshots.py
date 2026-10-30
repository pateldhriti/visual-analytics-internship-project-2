"""
Render static PNG snapshots of the four Story 5 charts for the React
Story 5 page (web/public/story5/), from the same warehouse views and the
same queries as etl/build_story5_dashboard.py's Superset charts.

Why images rather than a live embed: the Story 5 page presents four fixed
conclusions with their key insights, and a picture loads instantly with
no Superset dependency. The live dashboard is still linked from the page.
Re-run this after a data refresh so the images match the dashboard.

Styling follows the Superset charts: the project's "windsor_housing"
palette in the same slot order, slices sorted largest first (as Superset's
sort_by_metric does), donut pies with a direct label (name and share) on
every slice, and a bar chart for Story 4, whose conclusion is a ranking
rather than parts of a whole.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\render_story5_snapshots.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import StrMethodFormatter  # noqa: E402

from load_windsor_shelter_cost_to_postgres import get_engine  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "web" / "public" / "story5"

# docker/superset_config.py's "windsor_housing" scheme, same slot order.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK = "#2d2a32"
MUTED = "#6a6470"
GRID = "#e6dccb"
SURFACE = "#ffffff"
LABEL_GAP = 0.28  # minimum vertical space between two-line slice labels, in data units

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "text.color": INK,
    "axes.labelcolor": MUTED,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "figure.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})

QUERIES = {
    "tenure": """
        SELECT tenure AS label, SUM(burdened_households) AS value
        FROM warehouse.v_story1_burden_by_tenure
        GROUP BY tenure
    """,
    "zones": """
        SELECT zone_label AS label, SUM(rental_universe) AS value
        FROM warehouse.v_story2_zone_snapshot
        GROUP BY zone_label
    """,
    "starts": """
        SELECT dwelling_type AS label, SUM(units) AS value
        FROM warehouse.v_story3_windsor_supply_annual
        WHERE activity = 'Starts' AND period_year = 2025 AND dwelling_type <> 'Total'
        GROUP BY dwelling_type
    """,
    "rent": """
        SELECT REPLACE(market, ' CMA', '') AS label, AVG(average_rent_2br) AS value
        FROM warehouse.v_story4_rent_comparison
        WHERE period_label = 'Oct-25'
        GROUP BY market
    """,
}


def fetch(engine, key: str) -> pd.DataFrame:
    df = pd.read_sql(QUERIES[key], engine)
    df["value"] = df["value"].astype(float)
    return df.sort_values("value", ascending=False).reset_index(drop=True)


def donut(df: pd.DataFrame, title: str, subtitle: str, unit: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5.6), dpi=150)
    total = df["value"].sum()
    colors = PALETTE[: len(df)]
    wedges, _ = ax.pie(
        df["value"],
        colors=colors,
        startangle=90,
        counterclock=False,
        # 2px surface-coloured gaps between slices, so neighbours stay
        # distinct without relying on colour alone.
        wedgeprops={"width": 0.42, "edgecolor": SURFACE, "linewidth": 2},
    )

    # Direct label on every slice: name, share and count, in text ink
    # (not the slice colour), with a leader line to the slice. Labels are
    # placed per side of the donut and pushed apart vertically so small
    # neighbouring slices don't print on top of each other.
    labels = []
    for wedge, (_, row) in zip(wedges, df.iterrows()):
        angle = np.deg2rad((wedge.theta2 + wedge.theta1) / 2)
        x, y = np.cos(angle), np.sin(angle)
        share = 100 * row["value"] / total
        labels.append({
            "text": f"{row['label']}\n{share:.0f}%  ({row['value']:,.0f})",
            "anchor": (x * 0.98, y * 0.98),
            "side": 1 if x >= 0 else -1,
            "y": y * 1.22,
        })

    for side in (1, -1):
        on_side = sorted((lbl for lbl in labels if lbl["side"] == side), key=lambda lbl: -lbl["y"])
        for above, below in zip(on_side, on_side[1:]):
            below["y"] = min(below["y"], above["y"] - LABEL_GAP)

    for lbl in labels:
        ax.annotate(
            lbl["text"],
            xy=lbl["anchor"],
            xytext=(lbl["side"] * 1.32, lbl["y"]),
            ha="left" if lbl["side"] > 0 else "right",
            va="center",
            fontsize=9.5,
            color=INK,
            arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.8},
        )

    ax.text(0, 0.06, f"{total:,.0f}", ha="center", va="center", fontsize=18, fontweight="bold", color=INK)
    ax.text(0, -0.14, unit, ha="center", va="center", fontsize=9.5, color=MUTED)
    ax.set_aspect("equal")
    fig.suptitle(title, x=0.02, y=0.97, ha="left", fontsize=14, fontweight="bold", color=INK)
    fig.text(0.02, 0.905, subtitle, ha="left", fontsize=10, color=MUTED)
    # Wide side margins: slice labels sit outside the ring on both sides.
    fig.subplots_adjust(top=0.84, bottom=0.04, left=0.27, right=0.73)
    fig.savefig(path)
    plt.close(fig)


def rent_bars(df: pd.DataFrame, path: Path) -> None:
    # barh draws the first row at the bottom, so sort highest-first to put
    # the lowest rent (Windsor, the conclusion) at the top.
    df = df.sort_values("value", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5.6), dpi=150)
    bars = ax.barh(df["label"], df["value"], color=PALETTE[0], height=0.6)
    for bar, value in zip(bars, df["value"]):
        ax.text(value + 15, bar.get_y() + bar.get_height() / 2, f"${value:,.0f}", va="center", fontsize=10, color=INK)
    for tick in ax.get_yticklabels():
        if tick.get_text() == "Windsor":
            tick.set_fontweight("bold")
    ax.set_xlim(0, df["value"].max() * 1.15)
    ax.xaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="y", length=0, labelsize=10.5, labelcolor=INK)
    ax.set_xlabel("Average 2-bedroom apartment rent, October 2025")
    fig.suptitle("Windsor has the lowest 2-bedroom rent of five peer cities", x=0.02, y=0.97, ha="left",
                 fontsize=14, fontweight="bold", color=INK)
    fig.text(0.02, 0.905, "CMHC Rental Market Survey, Oct-25 -- a ranking, so bars rather than a pie",
             ha="left", fontsize=10, color=MUTED)
    fig.subplots_adjust(top=0.84, bottom=0.13, left=0.3, right=0.96)
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    engine = get_engine()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    donut(
        fetch(engine, "tenure"),
        "Renters are most of Windsor's cost-burdened households",
        "Households spending 30%+ of income on shelter, by tenure -- 2021 Census",
        "burdened households",
        OUTPUT_DIR / "story1-burdened-by-tenure.png",
    )
    donut(
        fetch(engine, "zones"),
        "Most of Windsor's rental stock is in the city's four zones",
        "Purpose-built rental units by zone -- CMHC Rental Market Survey, Oct-25",
        "rental units",
        OUTPUT_DIR / "story2-rental-stock-by-zone.png",
    )
    donut(
        fetch(engine, "starts"),
        "Apartments were most of Windsor's 2025 housing starts",
        "Housing starts by dwelling type, 2025 -- CMHC via StatCan 34-10-0154-01",
        "homes started",
        OUTPUT_DIR / "story3-starts-by-dwelling-type.png",
    )
    rent_bars(fetch(engine, "rent"), OUTPUT_DIR / "story4-rent-vs-peers.png")

    for png in sorted(OUTPUT_DIR.glob("*.png")):
        print(f"Wrote {png.relative_to(PROJECT_ROOT)} ({png.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
