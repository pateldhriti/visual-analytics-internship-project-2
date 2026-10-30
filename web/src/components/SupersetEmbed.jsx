// Embeds a Superset dashboard via a plain iframe against its public,
// anonymous-viewable URL -- Option A from docs/superset_embedding_research.md
// (Public role), not the Embedded SDK / guest-token route (Option B), which
// the team's own research and spike correctly deferred: this project has no
// backend server to mint guest tokens from, and every dataset here is meant
// to be fully public anyway, so there's nothing Option B's row-level
// security would add. Every dataset the embedded dashboard queries must be
// listed in docker/superset_config.py's PUBLIC_DATASOURCE_NAMES, or an
// anonymous viewer sees a permission error on that chart specifically.
const SUPERSET_DOMAIN = "http://localhost:8088";

// standalone=2 hides Superset's own top navbar AND the dashboard's title
// row (favorite star, Published badge, Edit Dashboard button) -- this
// page already shows its own title above, so that row is pure duplicate
// chrome. The native filter sidebar (Tenure, Household type) stays, since
// that's real functionality, not decoration.
export default function SupersetEmbed({ dashboardId, title, height = 1400 }) {
  const src = `${SUPERSET_DOMAIN}/superset/dashboard/${dashboardId}/?standalone=2`;
  const openUrl = `${SUPERSET_DOMAIN}/superset/dashboard/${dashboardId}/`;

  return (
    <div className="superset-embed card">
      <div className="superset-embed-header">
        <span className="superset-embed-badge">Live dashboard</span>
        <a href={openUrl} target="_blank" rel="noreferrer" className="superset-embed-link">
          Open full dashboard ↗
        </a>
      </div>
      <iframe
        src={src}
        title={title}
        className="superset-embed-frame"
        style={{ height }}
        loading="lazy"
      />
    </div>
  );
}
