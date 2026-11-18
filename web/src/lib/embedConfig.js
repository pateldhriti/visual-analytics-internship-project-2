// Settings shared by the dashboard embeds (SupersetGuestEmbed, SupersetEmbed).

// The Superset the site embeds: set VITE_SUPERSET_URL when building for another
// server (e.g. the university's); local Superset otherwise.
export const SUPERSET_DOMAIN = import.meta.env.VITE_SUPERSET_URL || "http://localhost:8088";

// `id` is a dashboard id or slug (the fixed URL name each builder sets, e.g.
// "windsor-story-1"); slugs stay the same on every Superset.
export const dashboardUrl = (id) => `${SUPERSET_DOMAIN}/superset/dashboard/${id}/`;

// "link": show each dashboard as a card that opens it on the Superset server
// instead of embedding it. For a Superset that does not allow embedding yet
// (the university's apss until its admin enables it): build with
// VITE_EMBED_MODE=link. Anything else embeds as usual.
export const EMBED_MODE = import.meta.env.VITE_EMBED_MODE || "embed";

// How long to wait for a dashboard before showing the error state.
export const LOAD_TIMEOUT_MS = 45000;
