# Hosted Superset Tuning: Caching, Redis, and Memory

**Status check first, honestly:** per `docs/hosting_decision.md`, no live VM exists yet -- Render is
deliberately deferred to ~Week 9, right before Demo Day, and no instance has ever been provisioned.
There is nothing to SSH into and tune today. What this task actually does instead: fix the real
caching/reliability gaps in this project's own `docker/docker-compose.yml` and
`docker/superset_config.py` -- the exact config that will run wherever this gets hosted, local or
Render -- so "dashboards load reliably" is true now, in dev, and carries over unchanged once a VM
exists.

## What was actually wrong

1. **Superset was running on its development server, not a production one.** `docker-compose.yml`'s
   command ended in `superset run -h 0.0.0.0 -p 8088` -- Superset's own docs explicitly say this is
   the Flask/Werkzeug dev server, single-threaded, not meant to serve real traffic. **Fixed**: now
   runs `gunicorn` with 2 worker processes, `gthread` worker class, 4 threads each, 120s timeout --
   Superset's own documented production pattern, sized modestly (2 workers) to fit a small/free-tier
   host rather than guessed at a large number.

2. **Only the metadata/chart-data cache was Redis-backed.** `CACHE_CONFIG`/`DATA_CACHE_CONFIG`
   already used Redis, but Superset's native-filter state and Explore-page form-data each have their
   *own* separate cache setting, and both default to `SimpleCache` (in-process memory) when not set
   explicitly -- confirmed directly from Superset's own defaults, not assumed. In-process memory
   doesn't survive a restart and isn't shared across multiple gunicorn workers -- with 2+ workers now
   running, a user's filter selection on this project's many native filters (Zone, Tenure, Dwelling
   Scope, Bedroom Type) could silently vanish depending on which worker handled the next request.
   **Fixed**: `FILTER_STATE_CACHE_CONFIG` and `EXPLORE_FORM_DATA_CACHE_CONFIG` added, Redis-backed,
   on their own DB indices (2, 3) separate from the main cache's DB 1 so clearing one doesn't clear
   the others.

3. **No explicit webserver timeout.** Superset's default (60s) can cut off a slower chart before it
   finishes rendering. This project's heaviest query
   (`v_dashboard1_cma_benchmark`'s `RANK() OVER` + grouped-median CTEs) runs well under that on this
   dev machine, but a smaller hosted VM could push it closer. **Fixed**: `SUPERSET_WEBSERVER_TIMEOUT
   = 120`, matching gunicorn's own `--timeout 120`.

4. **No memory ceiling on any container.** Fine for a dev machine with memory to spare; a real
   concern on a small/free-tier host where one container growing unbounded could starve the others.
   **Fixed**: `mem_limit: 1g` on the Superset container, `mem_limit: 128m` on Redis (its own `maxinfo`
   shows under 2 MB in use with this project's current dataset/chart count, so 128m is a generous
   floor, not a tight one).

## Verified live, not just configured on paper

Restarted the full stack (`docker compose --env-file .env -f docker/docker-compose.yml up -d`) with
all of the above applied, and confirmed directly:

- gunicorn actually boots and binds: `Listening at: http://0.0.0.0:8088`, 2 workers confirmed in the
  container logs.
- `GET /health` returns `200 OK`.
- A full API login + dashboard list + dashboard detail fetch still works end-to-end post-restart,
  and Dashboard 3's filter names (`Tenure`, `Household Type` -- see `docs/filter_standards.md`)
  persisted correctly through the restart, confirming the metadata DB and new cache config didn't
  break anything.
- Redis DB 1 shows real keys (`dbsize` = 3) immediately after those API calls, confirming the cache
  is actually being written to, not just configured and unused.

## What this does NOT claim

This is dev-environment tuning that will carry over to a hosted VM, not a report that a hosted VM
has been tested. When Render setup happens (~Week 9, per `docs/hosting_decision.md`), re-verify this
same checklist against the real instance -- worker count and memory limits in particular may need
adjusting for Render's actual free-tier resources (512 MB RAM on the free web service, per
`docs/hosting_comparison.md`), which is tighter than this dev machine and may be tight for Superset
specifically regardless of these settings -- a real risk worth flagging now rather than discovering
it at the Week 9 deployment window.
