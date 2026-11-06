# Embedding Prototype: Guest-Token Backend + Story 1 in React

Builds the piece `docs/embedding_spike.md` found missing -- a backend that mints Superset guest
tokens -- and uses it to embed Story 1's dashboard (Superset id 3) in its React page with the
Embedded SDK.

## How it fits together

```
Browser (Story 1 page)
  │ POST /api/guest-token {"dashboard": "story1"}      (same origin; Vite proxies /api)
  ▼
api/guest_token_server.py  ── admin session ──▶ Superset
  │   GET  /api/v1/dashboard/3/embedded        -> embedded UUID
  │   POST /api/v1/security/guest_token/       -> token scoped to that one dashboard
  ▼
{"token", "dashboardUuid", "supersetDomain"}
  │
  ▼
SupersetGuestEmbed.jsx -> embedDashboard() -> iframe /embedded/<uuid>, authenticated by the token
```

| Piece | File |
|---|---|
| Guest-token API (one endpoint, Python standard library + `requests`) | `api/guest_token_server.py` |
| Its tests (fake Superset client, no network) | `api/test_guest_token_server.py` |
| Turns on embedding for dashboards 3, 4, 7 and 6, sets allowed domains | `etl/enable_dashboard_embedding.py` (`enable_story1_embedding.py` now calls it for dashboard 3 only) |
| React embed with the SDK, falls back to the public iframe | `web/src/components/SupersetGuestEmbed.jsx` |
| Dev proxy for `/api` | `web/vite.config.js` |

## Design decisions

- **Allowlist by short name.** The browser asks for `"story1"`, not a Superset id. Only names in
  `EMBEDDABLE_DASHBOARDS` get a token; anything else is a 404 without contacting Superset. Adding a
  dashboard means one line there plus enabling embedding on it.
- **UUID looked up, not hardcoded.** The backend reads the embedded UUID from Superset and returns
  it with the token, so re-creating the embedded config doesn't break the frontend.
- **Admin credentials stay server-side.** Minting a token needs `can_grant_guest_token`; the
  browser only ever sees the short-lived token. Responses are `Cache-Control: no-store`.
- **No row-level security.** `rls` is empty: every dataset on this site is public anyway. The guest
  user gets the Public role's permissions (Superset's default `GUEST_ROLE_NAME`).
- **Fallback.** The backend is not part of the static site build. If `/api/guest-token` fails, the
  component renders the existing public-role iframe (`SupersetEmbed`) for the same dashboard, so
  the page never shows an empty box.
- **Height fits the dashboard.** After loading, the component asks the SDK for the dashboard's
  scroll height (`getScrollSize()`) and grows the frame to match. This addresses the
  scroll-inside-a-scroll issue in `docs/dashboard1_2_react_usability_review.md` (finding 3) for the
  SDK path; the public-iframe fallback still uses the fixed height.
- **No new dependencies.** Python's `http.server` is enough for one endpoint; `requests` was
  already used across `etl/` and is now listed in `requirements.txt`.

## Verified

Against the running local stack:

- `POST /api/guest-token {"dashboard": "story1"}` -> 200 with a token and dashboard 3's embedded
  UUID, through the Vite proxy (`http://localhost:5173/api/guest-token`) as well as directly.
- Unknown dashboard (`"story4"`) -> 404; non-JSON body -> 400.
- **The token alone works**: with only the `X-GuestToken` header (no session, no login), the chart
  data API returned Story 1's real figures (Renter 34.8%, Owner 10.9%).
- `GET /embedded/<uuid>` -> 200 with a `Referer` from `http://localhost:5173`, **403** from any
  other origin -- Superset enforces the embedded config's allowed domains.
- `etl/enable_story1_embedding.py` run twice -> same UUID both times.
- 13 backend tests pass; `npm run lint`, `format:check` and `build` pass.

**Not verified here:** the rendered dashboard inside the browser (no browser was available in this
environment). Open `http://localhost:5173/stories/affordability` with the API running; the
browser console logs a warning if the page fell back to the public iframe.

## Running it locally

```
.venv\Scripts\python.exe etl\enable_dashboard_embedding.py # once
.venv\Scripts\python.exe api\guest_token_server.py          # keep running (port 8090)
cd web && npm run dev                                      # proxies /api to 8090
```

Optional `.env` overrides: `SUPERSET_URL` (default `http://localhost:8088`),
`GUEST_TOKEN_API_HOST` / `GUEST_TOKEN_API_PORT` (default `127.0.0.1:8090`).

## Before this goes beyond local development

- Set `FRONTEND_ORIGINS` to the production site's origin for the API, for
  `etl/enable_dashboard_embedding.py` (re-run it) and for `docker/superset_config.py` (CSP
  `frame-ancestors`).
- Run the API behind the same reverse proxy as the site, so `/api` stays same-origin.
- Use a dedicated Superset service account with only `can_grant_guest_token` instead of the admin
  login.
- Rate limiting and origin checks are now in place (see below); behind a proxy, add the proxy's
  address to `GUEST_TOKEN_TRUSTED_PROXIES` so the limit applies per visitor.

## Update: all four dashboards, hardened endpoint (2026-11-06)

All four story pages now use the guest-token embed: `story1` (dashboard 3), `story2` (4), `story3`
(7) and `story4` (6). Each falls back to the public iframe if the API is down.

The endpoint is unauthenticated by design, so it now refuses anything that is not the site
calling it:

| Check | Response |
|---|---|
| `Origin` (or `Referer`) not in `FRONTEND_ORIGINS`, or missing | 403 |
| `Content-Type` not `application/json` (blocks plain HTML form posts) | 415 |
| Body over 1 KB | 413 |
| More than 30 requests a minute from one client | 429 with `Retry-After` |
| Unknown dashboard name | 404, Superset not contacted |

Every response carries `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`. The origin
check stops other websites from minting tokens through a visitor's browser; it does not stop a
script that forges headers, which is why the rate limit and the one-dashboard, short-lived token
scope remain the real limits. 29 tests in `api/test_guest_token_server.py` cover these cases.

**Loading and error states.** While a dashboard loads, the page shows a spinner with "Loading the
live dashboard…" (`role="status"`). If neither the secure embed nor the public iframe loads within
45 seconds, or Superset cannot be reached at all, it shows a message with **Try again** and a link
that opens the dashboard in a new tab (`role="alert"`). Components:
`web/src/components/EmbedStatus.jsx`, `SupersetGuestEmbed.jsx`, `SupersetEmbed.jsx`.

**Verified in Chrome** (Playwright): all four pages show the loading state, then the secure embed
renders its charts (10, 17, 9 and 7); with the token API returning 503 the public iframe loads;
with the API and Superset both unreachable the error state appears and Try again restarts loading;
clicking a zone in the embedded Story 2 dashboard updates its explanation panel.
