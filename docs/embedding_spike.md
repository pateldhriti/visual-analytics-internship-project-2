# Embedding Spike: Superset Embedded SDK with a Guest Token

**Goal:** actually embed one test dashboard in React using `@superset-ui/embedded-sdk` and a real
guest token, not just read the docs (`docs/superset_embedding_research.md` already did that) --
find out hands-on what breaks, and confirm or correct that research's recommendation with evidence.

**Result: the mechanism works end-to-end. The blocker is exactly what the research predicted --
confirmed, not just theorized.**

## What was built and verified, step by step

1. **`docker/superset_config.py`:** `FEATURE_FLAGS = {"EMBEDDED_SUPERSET": True}` and
   `GUEST_TOKEN_JWT_SECRET` (a real generated secret, `.env`/`.env.example`, not Superset's unsafe
   default). Restarted the container, confirmed both active via `current_app.config` in the
   Superset shell.
2. **Created a real test dashboard** (`Embedding Spike Test Dashboard`, id 1) containing the
   existing Story 1 chart, via the REST API -- none existed before this spike (confirmed in
   `docs/superset_embedding_research.md`'s own research).
3. **Enabled embedding** on it: `POST /api/v1/dashboard/1/embedded` with
   `allowed_domains: ["http://localhost:5173"]` -- got back a real UUID
   (`a37bce16-3fee-4097-9827-210061979192`).
4. **Minted a real guest token** from an admin service account (`POST /api/v1/security/guest_token/`)
   -- succeeded, 431-byte JWT.
5. **Proved the token actually works**, independent of the Public-role work from the earlier
   Superset-configuration task: used *only* the guest token (`Authorization: Bearer <token>`, no
   session cookie, no login) to fetch the chart's metadata and real data.
   **Result:** `Owner 10.9%, Renter 34.5%` -- the real figures, via guest-token auth alone.
6. **Installed `@superset-ui/embedded-sdk`** and built `web/src/pages/EmbedSpike.jsx` (not linked
   from site nav -- a throwaway test route, not a real page) wired to `embedDashboard()` with a
   correctly-written `fetchGuestToken()`. `npm run build`/`lint`/`format:check` all pass clean.

## The blocker: confirmed, not theoretical

**This project has no backend server to mint guest tokens from.** Superset's own docs are explicit
that `fetchGuestToken` must call your *own* server, never Superset's guest-token endpoint directly
from client code (that call needs an admin-level service-account credential, which can't be shipped
to a browser). `EmbedSpike.jsx`'s `fetchGuestToken()` correctly calls `/api/guest-token` on our own
origin, exactly as a real implementation should -- and that endpoint doesn't exist, because this
project is a static React site + Superset + Postgres with no custom API server anywhere. Every other
piece of the mechanism (feature flag, dashboard embedding, guest token minting, guest-token-scoped
data access) was proven to work in steps 1-5 above using the admin account to stand in for the
backend that doesn't exist yet.

This is exactly the blocker `docs/superset_embedding_research.md` identified from reading the docs,
before any code was written -- this spike confirms it's real by actually hitting it, not just
predicting it.

## Other things found along the way

- Restarting Superset to pick up the new `GUEST_TOKEN_JWT_SECRET` also recreated the Postgres
  container (`docker compose up` detected the `.env` change affected both services' config hash).
  **Not data loss** -- confirmed all 4 fact tables' row counts unchanged after the recreate (the
  named volume persisted) -- but worth knowing: a `.env` change can trigger a wider container
  recreate than expected.
- `allowed_domains` is set to `http://localhost:5173` only, for local dev -- would need updating
  per deployment environment (e.g. once the Oracle Cloud VM from `docs/hosting_comparison.md` is
  up), not a one-time setting.
- `npm install @superset-ui/embedded-sdk` surfaced 4 pre-existing dependency vulnerabilities
  (`esbuild`/`vite` dev-server issue, `react-router` open-redirect) -- confirmed via `npm audit`
  these are **pre-existing in `vite`/`react-router-dom`, not introduced by the SDK package itself**.
  Not this spike's to fix, but flagging so it isn't later mistaken for a new issue this work caused.

## Recommendation: unchanged from the research

This spike doesn't change `docs/superset_embedding_research.md`'s recommendation -- it strengthens
it. The guest-token mechanism genuinely works, but building the missing backend just to mint tokens
remains disproportionate effort for a site with no user accounts and no row-level-security use case
(every dataset here is already meant to be fully public). The Public-role approach already built
(same underlying `GUEST_ROLE_NAME = "Public"` default the guest token itself falls back to) gets the
same effective viewer access with none of this additional infrastructure. Keep `EmbedSpike.jsx` and
this config in the codebase as a working reference, in case a future user-accounts feature makes the
backend worth building -- but don't build the production backend now.
