// Shared KPI-tile row used on the homepage and every story page. Every
// value passed in must be a real, already-verified figure traced to a
// specific source (see each page's own SOURCE/DEFINITIONS data) -- this
// component only lays the tiles out, it never invents a number.
const TREND_GLYPH = { up: "↑", down: "↓", flat: "→" };

export default function KpiRow({ tiles }) {
  if (!tiles?.length) return null;

  return (
    <div className="kpi-tile-row">
      {tiles.map((tile) => (
        <div className="card kpi-tile" key={tile.label}>
          <span className={`kpi-tile-badge kpi-tile-badge--${tile.accent ?? "blue"}`} aria-hidden="true">
            {TREND_GLYPH[tile.trend] ?? "●"}
          </span>
          <p className="kpi-tile-value">{tile.value}</p>
          <p className="kpi-tile-label">{tile.label}</p>
          {tile.caption && <p className="kpi-tile-caption">{tile.caption}</p>}
        </div>
      ))}
    </div>
  );
}
