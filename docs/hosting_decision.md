# Hosting Decision

**Decision: Render**, set up deliberately close to final deployment (target: late November, ~Week 9
of the project roadmap) rather than now -- not Oracle Cloud, despite Oracle being
`docs/hosting_comparison.md`'s original top recommendation.

## What changed since that recommendation

`docs/hosting_comparison.md` recommended Oracle Cloud Always Free as the Week 2 hosting test,
specifically because it's the only option that's genuinely free for the full 11-week timeline with
enough resources to run the existing `docker-compose.yml` as-is. That recommendation was sound on
paper. In practice, the Week 2 test itself never got past **account signup**:

1. First attempt: generic "account not created" failure, no specific field flagged.
2. Second attempt: Oracle's own fraud/identity-verification rejection -- "unable to complete your
   sign up," citing incomplete/inaccurate info, masked location, or a duplicate-account attempt as
   the possible causes, with no way to tell which applied.

This is a **real, documented blocker in Oracle's own signup flow**, not a problem with Oracle's
service itself, and not something this project's tooling could resolve (account creation needs a
real payment method, a real phone for SMS verification, and browser interaction -- none of which
are things an automated assistant can do on someone's behalf). No VM was ever provisioned, so there
is no live-instance test data to report -- this decision is made without one, honestly, rather than
inventing results from a test that didn't happen.

## Why Render, given that

`docs/hosting_comparison.md` already evaluated Render and flagged its real limitation: the free
Postgres database **expires 30 days after creation**, shorter than the project's 11-week span if set
up too early. That limitation is exactly why Render wasn't the original top pick -- but it stops
being disqualifying once hosting isn't needed for the full 11 weeks, only for final deployment
through Demo Day.

- **Free web service** (512 MB RAM, sleeps after 15 min idle) -- acceptable for a project demo site,
  not acceptable for a product with continuous traffic, which this isn't.
- **Free Postgres**, 1 GB storage, 30-day expiry -- the real constraint, managed by timing rather
  than avoided.

## The actual decision: timing, not just the platform

Render will be set up **roughly 3-4 weeks before Demo Day** (per the proposal's roadmap, final
deployment is Week 9, Nov 23-Nov 29, and Demo Day is Week 11, Dec 7-9) -- not now. Setting it up
today would have the free database expire well before the project needs it live. This timing is the
actual mitigation for Render's one real limitation, not a workaround that's being glossed over.

## What's not being done

- **Oracle Cloud is not abandoned outright** -- if the signup issue resolves on its own retry or via
  Oracle support before Render's setup window opens, Oracle remains the better long-term option
  (more resources, no expiry) and the team can switch. This decision is "use Render for now, timed
  deliberately," not "Oracle is permanently ruled out."
- **Railway** stays the documented fallback-of-last-resort ($5/month after a 30-day trial) if
  Render's sleep-after-15-min behavior turns out to be a real problem for a live demo.
- **No live infrastructure test has been run against either platform yet.** This document is a
  decision about *which platform and when*, not a report that Render has been tested and confirmed
  working -- that test is still a real task for closer to the Week 9 deployment window.
