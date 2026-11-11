"""
Draw the simplified star schema used as Figure 3 in docs/design_document
(.md and .docx): dimensions in blue, fact tables in green, solid lines for
foreign keys, and a dashed line for the city-name join Story 5 uses to bring
in the comparison cities (fact_peer_cma_context).

Run from the project virtual environment:
    .venv\\Scripts\\python.exe docs\\diagrams\\draw_star_schema.py
Writes docs/diagrams/star_schema_simplified.png (1659 x 956 px).
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

OUT = Path(__file__).with_name("star_schema_simplified.png")
W, H, DPI = 1659, 956, 200

DIM_FILL, FACT_FILL = "#e8f0fb", "#e3f4ec"
EDGE, INK, LINK, JOIN = "#85828e", "#2b2b33", "#c4c2cc", "#d0703c"

# name: (centre x, centre y, width, height) in pixels, y measured from the top
DIMS = {
    "dim_household_type": (202, 101, 342, 78),
    "dim_income_band": (771, 101, 342, 78),
    "dim_bedroom_type": (1411, 101, 342, 78),
    "dim_tenure": (771, 259, 342, 78),
    "dim_geography": (353, 502, 342, 78),
    "dim_period": (771, 502, 342, 78),
    "dim_zone": (1190, 502, 342, 78),
}
FACTS = {
    "fact_shelter_cost": (365, 259, 470, 108),
    "fact_rental_market": (1178, 259, 470, 108),
    "fact_windsor_starts_completions": (290, 745, 440, 100),
    "fact_census_profile": (771, 745, 400, 100),
    "fact_rental_market_comparison": (1252, 745, 470, 100),
    "fact_peer_cma_context": (1252, 890, 470, 82),
}
LINKS = [
    ("dim_household_type", "fact_shelter_cost"),
    ("dim_income_band", "fact_shelter_cost"),
    ("dim_income_band", "fact_rental_market"),
    ("dim_bedroom_type", "fact_rental_market"),
    ("dim_tenure", "fact_shelter_cost"),
    ("dim_tenure", "fact_rental_market"),
    ("dim_geography", "fact_shelter_cost"),
    ("dim_geography", "fact_census_profile"),
    ("dim_period", "fact_shelter_cost"),
    ("dim_period", "fact_rental_market"),
    ("dim_period", "fact_census_profile"),
    ("dim_period", "fact_windsor_starts_completions"),
    ("dim_period", "fact_rental_market_comparison"),
    ("dim_zone", "fact_rental_market"),
    ("dim_zone", "fact_rental_market_comparison"),
]
BOXES = {**DIMS, **FACTS}


def edge_point(box, toward):
    """Where the line from a box's centre toward another point leaves the box."""
    cx, cy, w, h = box
    dx, dy = toward[0] - cx, toward[1] - cy
    if dx == 0 and dy == 0:
        return cx, cy
    scale = min((w / 2) / abs(dx) if dx else float("inf"), (h / 2) / abs(dy) if dy else float("inf"))
    return cx + dx * scale, cy + dy * scale


def main() -> None:
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")

    for a, b in LINKS:
        p1 = edge_point(BOXES[a], BOXES[b][:2])
        p2 = edge_point(BOXES[b], BOXES[a][:2])
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=LINK, lw=1.2, zorder=1)

    # Story 5's join on city name: not a foreign key, so dashed.
    a, b = FACTS["fact_rental_market_comparison"], FACTS["fact_peer_cma_context"]
    ax.plot([a[0], b[0]], [a[1] + a[3] / 2, b[1] - b[3] / 2], color=JOIN, lw=1.6, ls=(0, (4, 3)), zorder=1)
    ax.text(a[0] + 12, (a[1] + a[3] / 2 + b[1] - b[3] / 2) / 2, "city (CMA)", color=JOIN, fontsize=6.5,
            va="center", ha="left", style="italic")

    for name, (cx, cy, w, h) in BOXES.items():
        fill = FACT_FILL if name.startswith("fact") else DIM_FILL
        ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0,rounding_size=8",
                                    fc=fill, ec=EDGE, lw=1.1, zorder=2))
        ax.text(cx, cy, name, ha="center", va="center", fontsize=8, fontweight="bold", color=INK, zorder=3)

    ax.text(771, 385, "Shared dimensions (tenure, income, period, geography)\nare what let the stories be combined",
            ha="center", va="center", fontsize=7, style="italic", color="#666470")
    ax.text(40, 905, "Solid: shared dimension keys\nDashed: Story 5 join on city name", ha="left", va="center",
            fontsize=6.5, color="#666470")

    fig.savefig(OUT, dpi=DPI, facecolor="white")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
