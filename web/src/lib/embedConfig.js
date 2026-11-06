// Settings shared by the dashboard embeds (SupersetGuestEmbed, SupersetEmbed).

export const SUPERSET_DOMAIN = "http://localhost:8088";

export const dashboardUrl = (id) => `${SUPERSET_DOMAIN}/superset/dashboard/${id}/`;

// How long to wait for a dashboard before showing the error state.
export const LOAD_TIMEOUT_MS = 45000;
