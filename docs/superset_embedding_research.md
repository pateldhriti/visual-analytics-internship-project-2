# Embedding Research — Superset Embedded SDK (guest tokens) vs. Public Dashboards

**Why this matters for us:** the React site needs to show Superset charts/dashboards to anonymous
visitors with no login (per the proposal's vision: "give anyone with a web browser" access). There
are two genuinely different ways Superset supports that, and they have different security models,
setup effort, and hosting requirements. This compares both against our actual architecture — a
static React site + Superset + Postgres, no custom backend API server — rather than in the
abstract.

## Option A: Public dashboards (anonymous Public role)

**How it works:** Superset auto-assigns every unauthenticated request the built-in `Public` role.
Grant that role `datasource_access` on specific datasets (plus `can_read` on Chart/Dashboard/
Dataset), and anyone can view charts/dashboards built on those datasets with zero login, zero
token, zero per-viewer logic — a plain iframe or API call against the public Superset URL works
directly.

**Already built and verified** — `docker/superset_config.py`'s `PUBLIC_ROLE_LIKE_GAMMA` +
`FLASK_APP_MUTATOR` (this project's own Superset-configuration work): confirmed a genuinely
unauthenticated session can fetch real chart data with zero authentication.

**Setup effort:** low. No backend component beyond Superset itself — the thing we're already
running. No new service to build, deploy, or host.

**Security model:** access is all-or-nothing per dataset. Whatever's granted to `Public` is visible
to literally anyone who finds the URL, indefinitely, with no expiry and no per-viewer row filtering.
The Public role can also read embedded dashboards (Option B), so a misconfigured Public role exposes
embed content too — the two options aren't fully isolated from each other.

**Hosting needs:** none beyond the existing Docker stack (Postgres + Superset + Redis).

## Option B: Embedded SDK (guest tokens)

**How it works:** the host app's *own backend* calls Superset's `POST /api/v1/security/guest_token/`
(a service account with the `can_grant_guest_token` permission) to mint a short-lived JWT scoped to
a specific dashboard, optionally with row-level-security (RLS) rules and a dataset allowlist. The
frontend passes that token to `@superset-ui/embedded-sdk`'s `embedDashboard()`, which renders the
dashboard in a sandboxed iframe. Guest tokens default to the `Public` role too
(`GUEST_ROLE_NAME = "Public"`) unless reconfigured.

**Setup effort:** moderate-to-high, and the big one for us specifically: **it requires a backend
server to mint tokens** — `fetchGuestToken` must call Superset from server-side code; the docs are
explicit that this must never be called from the client. We don't have a backend API server at all
right now (React site is static, talks to Superset/Postgres directly or not at all) — adding one
*just* to mint guest tokens is new infrastructure, not a config change. Beyond that: enable
`EMBEDDED_SUPERSET` feature flag, set a strong `GUEST_TOKEN_JWT_SECRET` (the default is explicitly
unsafe for production), set per-dashboard **Allowed Domains** (checked against the request's
`Referer` header — an empty list allows any origin, so must be set explicitly), get each
dashboard's embedding UUID, install the npm package, and wire token refresh into the frontend
before each ~5-minute-default expiry (`GUEST_TOKEN_JWT_EXP_SECONDS`).

**Security model:** meaningfully stronger *when there's something to scope*. Tokens expire, can be
bound to specific datasets (allowlist), and can carry RLS rules to filter rows per viewer. But RLS
scoping is a benefit only when different viewers should see different data — our site has no user
accounts or login at all, so every anonymous visitor would get the identical token payload. The
main security win Option B offers doesn't apply to how this project is actually used.

**Hosting needs:** the existing Docker stack **plus** a server-side component to mint tokens
(a small API endpoint somewhere) -- real additional infrastructure on top of what Option A needs,
on an already resource-constrained free-tier VM (`docs/hosting_comparison.md`).

## Recommendation: Public dashboards (Option A), not the Embedded SDK

Three reasons, specific to this project rather than a general "which is more secure" comparison:

1. **We have no backend to mint guest tokens from.** Option B's entire setup assumes a server-side
   component that calls Superset on the frontend's behalf. Building one just to issue tokens is
   disproportionate infrastructure for a site that otherwise needs none.
2. **The data is already meant to be fully public.** Every dataset in this project comes from open
   government sources (StatCan, CMHC) with no row-level restriction ever needed -- the exact
   scenario RLS guest tokens exist to handle (different viewers see different rows) doesn't apply
   here.
3. **It's already built, verified, and fits the existing hosting plan** -- no new service, no new
   component to deploy to the Oracle Cloud Always Free VM once that's up.

**The real risk to manage going forward isn't technical, it's discipline:** every dataset added to
`PUBLIC_DATASOURCE_NAMES` in `docker/superset_config.py` is visible to anyone, indefinitely, with no
expiry or revocation the way a guest token has. Review that list deliberately whenever a new
chart/dashboard is added -- don't grant Public access to a dataset by default.

**When to revisit this:** if the project ever adds real user accounts or a reason to show different
data to different viewers, Option B's RLS scoping becomes the actual right tool -- revisit then, not
now.

## Sources

- [Superset Embedded SDK README](https://apache.googlesource.com/superset/+show/HEAD/superset-embedded-sdk/README.md) -- guest token flow, config, security notes
- [Using Superset -- Embedding dashboards](https://superset.apache.org/user-docs/using-superset/embedding) -- setup steps, feature flags, Allowed Domains
- [Apache Superset Security docs](https://superset.apache.org/admin-docs/security/) -- Public role, DASHBOARD_RBAC
- [Configuring Apache Superset for public and embeddable dashboards (community forum)](https://forum.yunohost.org/t/configuring-apache-superset-for-public-and-embeddable-dashboards/32533) -- real-world note that Public role setup needs more than just the feature flag, consistent with what this project's own Superset-configuration work found
