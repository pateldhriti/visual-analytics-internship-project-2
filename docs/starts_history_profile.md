# Profile: 2015-2025 Starts History (CMHC Quarterly Starts/Completions/Under Construction)

**Goal:** check older editions of CMHC's Quarterly Starts, Completions, Units Under Construction
table for dwelling-type naming changes, and build a mapping table if any are found.

**Status: blocked before a mapping table could be built -- documented honestly below, not
fabricated.** Two real, concrete blockers found while actually trying, not assumed in advance.

## What's confirmed from the one real file this project has

The current edition (`data/raw/cmhc/quarterly-starts-completions-under-construction-06-26-en.xlsx`,
published 2026, covering Second Quarter 2026) uses these 5 dwelling-type columns:

```
Singles, Semis, Row, Apartment and Other, Total
```

This is the only edition's actual column names this project can currently verify directly --
everything below is about why no second, older edition could be obtained to compare against it.

## Blocker 1: the table's own edition history doesn't go back to 2015

CMHC's "Quarterly Starts, Completions and Under Construction (Canada, provinces)" page has an
edition selector. Checked directly: it lists 22 editions, **March 2021 through June 2026** -- and
nothing earlier. If 2015-2020 editions of this specific table exist anywhere, they aren't reachable
through this table's own page. (CMHC's "Archived" section on its broader housing-market-data page
lists 2 general headings -- "Housing Starts, Completions and Units Under Construction" and its
Cumulative counterpart -- with no dates or file links shown, so whether those archives reach back to
2015 for this specific table couldn't be confirmed from this project's tooling either.)

## Blocker 2: the download control isn't a stable, fetchable URL

The page's Download button is a placeholder link (`href="#"`), not a direct file URL -- confirmed by
reading the page's actual markup, not assumed. Getting a file (current or any older edition selected
from the dropdown) requires clicking through CMHC's website UI, which needs browser automation. No
browser-automation tool was available in this session to do that click-through -- `WebFetch` reads
page text but can't execute the download action, and a direct `.xlsx` URL couldn't be found via
search either (tried `filetype:xlsx` search, no direct link surfaced).

## What would actually close this gap

1. **Manually download each of the 22 available editions** (March 2021-June 2026) through CMHC's
   website UI -- the edition selector + Download button -- and drop them into `data/raw/cmhc/`
   (e.g. `quarterly-starts-completions-under-construction-03-21-en.xlsx`, etc.). Once the files
   exist locally, profiling their dwelling-type column names and building the mapping table is
   straightforward (the same `openpyxl` read already used by
   `etl/extract_cmhc_starts_completions.py` works on any edition with the same sheet layout).
2. **For 2015-2020 specifically**, check whether CMHC's Housing Information Monthly PDF archive
   (this table was formerly "Volume C" in that report, per the current page's own note) has older
   editions -- a different source than the Excel table's own edition selector, not yet checked in
   this project.

## Why no mapping table is included here

A mapping table with only one real edition's column names (the current one) wouldn't be a mapping
of anything -- there's nothing to map it *against* yet. Publishing a table that implies dwelling-type
naming has been checked across 2015-2025 when only one year's naming is actually known would be
exactly the kind of fabricated-but-real-looking output this project has consistently avoided
elsewhere (see `sql/story3_views.sql` and `docs/affordability_gap_index.md` for the same honest-gap
pattern). This profile is a real, useful finding on its own -- it tells the next person exactly what
blocks this task and what two things would unblock it -- even though it isn't the mapping table the
ticket originally asked for.
