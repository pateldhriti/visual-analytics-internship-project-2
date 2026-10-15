# Story 3 — "What does housing supply look like?" (Narrative v1)

**Guiding questions (proposal section 4.3):**
- How many housing units are being started and completed, and which dwelling types contribute most?
- How can supply activity be interpreted alongside Windsor population and household context?

**Status:** first draft. Grounded entirely in real, verified figures from `warehouse.fact_starts_completions` and `warehouse.fact_census_profile` (see `docs/data_quality_report.md` for the validation behind the supply numbers). A "Data gaps" section at the end is deliberate, not an oversight — this story cannot be told at the Windsor level yet, and the narrative says so rather than quietly working around it.

---

## Draft text

Ontario added 17,786 new housing units in the second quarter of 2026, according to CMHC's construction survey — and the story of *what kind* of housing that number represents is at least as telling as the total itself. Apartments (CMHC's "Apartment and Other" category) accounted for 12,547 of those starts, 70% of everything built. Row housing came next at 2,262 (13%), then singles at 2,693 (15%), with semi-detached homes a distant fourth at 284 (2%). Ontario's new supply, in other words, is overwhelmingly multi-unit — a pattern that holds across the first half of 2026 too: 31,779 starts year-to-date, with the same apartment-led mix.

Completions tell a related but distinct story. Ontario completed 14,083 units in the same quarter — about 3,700 fewer than it started, a gap that shows up again at the national level (Canada started 66,788 units against 60,485 completions). That gap isn't evidence of a slowdown on its own: completions lag starts by the length of a construction project, so a quarter with more starts than completions is consistent with a pipeline that's still filling, not necessarily one that's falling behind. What it does confirm is scale: 162,138 units are under construction in Ontario right now, over 11 times the quarter's own completions — a large pipeline relative to current throughput, regardless of which number you compare it to.

Canada as a whole mirrors Ontario's shape closely enough that Ontario looks like a reasonably representative slice of the national pattern, not an outlier: Ontario's 17,786 quarterly starts are roughly a quarter of Canada's 66,788, in line with Ontario's general share of national population and construction activity.

## How this compares to Windsor's own context

Windsor CMA's 2021 Census shows a population of 422,630 across 165,665 occupied private dwellings. That's real, useful context for *scale* — it tells us roughly how large Windsor's housing stock already is — but it cannot yet be connected to the construction numbers above in any rigorous way, for a reason worth stating plainly rather than glossing over.

## Data gaps affecting this story

1. **No Windsor-specific starts/completions figure exists in this project's data.** The CMHC table extracted so far ("Quarterly Starts, Completions, Units Under Construction by Canada, Provinces") reports Ontario and Canada totals only — it has no CMA-level breakdown. Every number in the draft above is provincial or national, not Windsor's. Closing this gap requires extracting a different, CMA-level CMHC table (e.g. "Starts, Completions, and Units Under Construction by Geography") — CMHC does publish Windsor-specific starts (though provincial-level completions reporting was discontinued after Jan 2023, so even a CMA table may not give every metric this story wants).
2. **Only one quarter of data exists, not a time series.** "Is Windsor building enough housing" is fundamentally a question about trend — is supply keeping pace, speeding up, slowing down — and a single quarter (Second Quarter 2026) plus its own year-to-date figure cannot answer that. `docs/data_quality_report.md`'s supply-table section documents this explicitly: every prior quarter CMHC has published is currently missing from this project.
3. **"Supply per 1,000 households" cannot be computed yet**, for the geography-mismatch reason documented in `sql/story3_views.sql`: Windsor's household count (165,665) and this quarter's starts count (Ontario/Canada-only) don't share a geography, so dividing one into the other would produce a number that looks real but measures nothing real.

**What v2 of this narrative needs:** a CMA-level CMHC starts/completions table (to get Windsor specifically) and at least 3-4 additional historical quarters (to show direction, not just a snapshot). Once both exist, the "alongside Windsor population and household context" half of the guiding question becomes answerable for real, rather than gestured at with provincial proxies.
