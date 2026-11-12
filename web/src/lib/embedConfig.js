// Settings shared by the dashboard embeds (SupersetGuestEmbed, SupersetEmbed).

// The Superset the site embeds: set VITE_SUPERSET_URL when building for another
// server (e.g. the university's); local Superset otherwise.
export const SUPERSET_DOMAIN = import.meta.env.VITE_SUPERSET_URL || "http://localhost:8088";

// `id` is a dashboard id or slug (the fixed URL name each builder sets, e.g.
// "windsor-story-1"); slugs stay the same on every Superset.
export const dashboardUrl = (id) => `${SUPERSET_DOMAIN}/superset/dashboard/${id}/`;

// How long to wait for a dashboard before showing the error state.
export const LOAD_TIMEOUT_MS = 45000;
