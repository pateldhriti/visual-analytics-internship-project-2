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
sort_by_metric does), donut pies with a key giving each slice's name, share and count, and a bar chart for Story 4, whose conclusion is a ranking
rather than parts of a whole.

Run from the project virtual environment:
    .venv\\Scripts\\python.exe etl\\render_story5_snapshots.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from matplotlib.ticker import MultipleLocator, StrMethodFormatter  # noqa: E402

from load_windsor_shelter_cost_to_postgres import get_engine  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "web" / "public" / "story5"

# docker/superset_config.py's "windsor_housing" scheme, same slot order.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK = "#2d2a32"
MUTED = "#6a6470"
GRID = "#e6dccb"
SURFACE = "#ffffff"

# The React page shows each image at roughly half its pixel width, so the
# figure is kept small in inches and text large relative to it -- labels
# land around 13px on screen, not 9px.
FIGSIZE = (7.2, 4.6)
DPI = 190
LABEL_SIZE = 11

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


def add_caption(fig, caption: str) -> None:
    """What the chart measures and where it's from. No headline: the React
    card above each image already carries the conclusion as its title."""
    fig.text(0.02, 0.955, caption, ha="left", va="center", fontsize=LABEL_SIZE, color=MUTED)


def donut(df: pd.DataFrame, caption: str, unit: str, path: Path) -> None:
    """Donut on the left, a key on the right with one row per slice
    (swatch, name, share and count) in the same largest-first order as the
    slices. A key rather than labels around the ring: with 7 zones, several
    small slices sit side by side and their labels collide or run off the
    image at the size the React card shows it."""
    fig = plt.figure(figsize=FIGSIZE, dpi=DPI)
    ax = fig.add_axes([0.02, 0.04, 0.46, 0.82])
    total = df["value"].sum()
    colors = PALETTE[: len(df)]
    ax.pie(
        df["value"],
        colors=colors,
        startangle=90,
        counterclock=False,
        # 2px surface-coloured gaps between slices, so neighbours stay
        # distinct without relying on colour alone.
        wedgeprops={"width": 0.38, "edgecolor": SURFACE, "linewidth": 2},
    )
    ax.text(0, 0.1, f"{total:,.0f}", ha="center", va="center", fontsize=20, fontweight="bold", color=INK)
    ax.text(0, -0.17, unit, ha="center", va="center", fontsize=LABEL_SIZE - 1, color=MUTED)
    ax.set_aspect("equal")

    # Key rows, vertically centred on the donut. Text stays in ink, not the
    # slice colour; the swatch carries the colour.
    row_height = min(0.115, 0.8 / len(df))
    top = 0.45 + row_height * (len(df) - 1) / 2
    for i, (color, (_, row)) in enumerate(zip(colors, df.iterrows())):
        y = top - i * row_height
        fig.patches.append(
            Rectangle((0.52, y - 0.022), 0.022, 0.044, transform=fig.transFigure, color=color, figure=fig)
        )
        share = 100 * row["value"] / total
        fig.text(0.56, y + 0.012, row["label"], ha="left", va="center", fontsize=LABEL_SIZE, color=INK)
        fig.text(0.56, y - 0.03, f"{share:.0f}%  ·  {row['value']:,.0f}", ha="left", va="center",
                 fontsize=LABEL_SIZE - 1, color=MUTED)

    add_caption(fig, caption)
    fig.savefig(path)
    plt.close(fig)


def rent_bars(df: pd.DataFrame, path: Path) -> None:
    # barh draws the first row at the bottom, so sort highest-first to put
    # the lowest rent (Windsor, the conclusion) at the top.
    df = df.sort_values("value", ascending=False)
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    bars = ax.barh(df["label"], df["value"], color=PALETTE[0], height=0.6)
    for bar, value in zip(bars, df["value"]):
        ax.text(value + 15, bar.get_y() + bar.get_height() / 2, f"${value:,.0f}", va="center", fontsize=LABEL_SIZE, color=INK)
    for tick in ax.get_yticklabels():
        if tick.get_text() == "Windsor":
            tick.set_fontweight("bold")
    ax.set_xlim(0, df["value"].max() * 1.15)
    ax.xaxis.set_major_locator(MultipleLocator(500))
    ax.xaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="y", length=0, labelsize=LABEL_SIZE, labelcolor=INK)
    ax.tick_params(axis="x", labelsize=LABEL_SIZE - 1)
    add_caption(fig, "Average 2-bedroom apartment rent -- CMHC Rental Market Survey, Oct-25")
    fig.subplots_adjust(top=0.88, bottom=0.09, left=0.37, right=0.95)
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    engine = get_engine()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    donut(
        fetch(engine, "tenure"),
        "Households spending 30%+ of income on shelter, by tenure -- 2021 Census",
        "burdened households",
        OUTPUT_DIR / "story1-burdened-by-tenure.png",
    )
    donut(
        fetch(engine, "zones"),
        "Purpose-built rental units by zone -- CMHC Rental Market Survey, Oct-25",
        "rental units",
        OUTPUT_DIR / "story2-rental-stock-by-zone.png",
    )
    donut(
        fetch(engine, "starts"),
        "Housing starts by dwelling type, 2025 -- CMHC via StatCan 34-10-0154-01",
        "homes started",
        OUTPUT_DIR / "story3-starts-by-dwelling-type.png",
    )
    rent_bars(fetch(engine, "rent"), OUTPUT_DIR / "story4-rent-vs-peers.png")

    for png in sorted(OUTPUT_DIR.glob("*.png")):
        print(f"Wrote {png.relative_to(PROJECT_ROOT)} ({png.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
