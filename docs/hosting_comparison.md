# Free Hosting Comparison — Oracle Cloud, Render, Railway

**Why this matters for us:** the stack is PostgreSQL + Apache Superset (+ Redis) + a React frontend, running for the full 11-week semester. Superset in particular is memory-hungry (realistically needs 2-4 GB+ to run comfortably alongside Postgres), and we already have a working `docker-compose.yml` that runs all three services together locally. The right host is whichever lets that same setup keep running, for free, for 11 weeks straight — not just whichever has the biggest numbers on a pricing page.

## Comparison

| | RAM / CPU | Storage | Sleep / uptime | Cost for 11 weeks | Confidence |
|---|---|---|---|---|---|
| **Oracle Cloud Always Free** | 2 OCPU + 12 GB RAM (Ampere A1 VM, splittable across up to 2 instances) | 200 GB block storage; separate 20 GB if using their Autonomous DB (we wouldn't — we'd run our own Postgres on the VM) | No sleep — it's a real persistent VM | $0, indefinitely (not a trial) | High — pulled from docs.oracle.com |
| **Render** | Free web service: 512 MB RAM, 0.1 shared CPU | Free Postgres: 1 GB storage, **expires 30 days after creation** (14-day grace period, then deleted) | Free web service sleeps after 15 min idle; ~1 min cold-start on next request | $0, but the database would need to be recreated/migrated mid-project (30-day expiry is shorter than our 11-week timeline) | High — pulled from render.com/docs |
| **Railway** | Trial: 1 GB RAM, 2 vCPU. After the 30-day trial, Hobby plan is $5/month minimum | Trial: 1 GB ephemeral + 0.5 GB volume storage | No documented sleep policy — but the app simply stops when credit runs out | **Not actually free past 30 days** — $5 one-time trial credit, then a real subscription | Medium — official docs, but Railway's own pages disagree on exact Hobby-plan limits |

**University server:** not available to this team — we don't have one, so it's out of scope for this comparison rather than an open question.

## Fit for our specific stack

- **Oracle Cloud Always Free** is the only option that gives us a real VM rather than separate managed services per container. That means we can run our *existing* `docker-compose.yml` (Postgres + Superset + Redis together) basically as-is, with no per-service free-tier expiry to track. The 12 GB RAM comfortably fits Superset + Postgres + Redis together. This is a strong match.
- **Render** fits a simple always-on container poorly here: the free *web service* sleeps after 15 minutes, which means Superset dashboards would cold-start (~1 min) for anyone who visits after a quiet period — not great for a "public website" demo. The bigger problem is the free Postgres database **expires in 30 days**, well inside our 11-week window, so we'd be stuck migrating mid-semester or paying. (One caveat: Render's free *static site* hosting, separate from web services, reportedly doesn't sleep — if true, it could still be useful for the React frontend specifically. Not confirmed in this research; worth a quick check before relying on it.)
- **Railway** isn't actually a free tier for our timeline — it's a 30-day trial. Past that, Hobby is $5/month minimum plus usage. Rules it out if the goal is genuinely $0 for the semester.

## Known risk with Oracle (flagging honestly, not hiding it)

Oracle's Always Free Arm allocation was cut in 2026 (previously 4 OCPU/24 GB, now 2 OCPU/12 GB), and multiple user reports describe "Out of Capacity" errors when first provisioning a free Arm instance, plus instances being disabled if usage is reported to exceed the new limit. This is a real, documented risk — not guaranteed smooth. Worth provisioning it early (Week 2) specifically to find out if capacity is available in our region before relying on it.

## Recommendation for the Week 2 hosting test

1. **Provision an Oracle Cloud Always Free Arm VM** and test deploying our existing `docker-compose.yml` to it. This is the only option that's genuinely free for the full 11 weeks and matches our current local setup almost exactly.
2. **Do not plan around Render or Railway** as the main host — Render's DB expiry (30 days) and Railway's trial expiry (30 days) are both shorter than our project timeline. Render's free static-site hosting could still be worth a quick separate check for the React frontend only, once we're further along.

## Sources

- [Always Free Resources — Oracle Cloud Infrastructure Documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [FAQ on Oracle's Cloud Free Tier](https://www.oracle.com/cloud/free/faq/)
- [OCI Always Free: Updated Ampere A1 Compute Allocation — Oracle Cloud Customer Connect](https://community.oracle.com/customerconnect/discussion/970310/oci-always-free-updated-ampere-a1-compute-allocation)
- [Deploy for Free — Render Docs](https://render.com/docs/free)
- [All New Free Instance Types On Render](https://render.com/blog/free-tier)
- [Pricing Plans — Railway Docs](https://docs.railway.com/pricing/plans)
- [Pricing — Railway](https://railway.com/pricing)
