# CMHC Starts/Completions Workbook — Audit Note

**Source file:** `data/raw/cmhc/quarterly-starts-completions-under-construction-06-26-en.xlsx` — CMHC "Quarterly Starts, Completions, and Under Construction (Canada and Provincial)," edition dated Second Quarter 2026.
**9 sheets total**, confirmed by reading the workbook directly: Index, Notes, Table C1, Table C2, Table C3, Table C4, Symbols, Coverage and Geography, Concepts and Definitions.

## Finding Windsor tables: there are none

This workbook has **no Windsor-specific table, and no Windsor row anywhere in any table.** Checked exhaustively, not sampled: every cell in all four data tables (C1–C4) was searched for the string "Windsor" — zero matches. The only geography values present across the whole workbook are the 10 provinces plus "Canada":

```
Alberta, British Columbia, Canada, Manitoba, New Brunswick, Newfoundland and
Labrador, Nova Scotia, Ontario, Prince Edward Island, Québec, Saskatchewan
```

This isn't a download mistake — it's what the title says: this edition is explicitly "Canada and Provincial," with no CMA-level breakdown at all. The task's premise ("find the Windsor tables") doesn't hold for *this specific file*; a different, CMA-level CMHC table is needed to get Windsor's own figures. The project proposal already names the right one in its own references (§7, ref. [5]): **"Starts, Completions and Units Under Construction by Geography"** — that table has not been downloaded yet.

One real, useful piece of context from the workbook's own **Notes** sheet: as of 2023, CMHC "only collects Completions and Under Construction data in CMAs (population 100,000+)." Windsor CMA (population 422,630, per the project's own Census Profile extraction) comfortably qualifies, so Windsor-specific completions/under-construction data does exist at CMHC — it's just rolled up into this file's Ontario/Canada totals rather than published per-CMA here. The province/Canada figures in this workbook are *built from* CMA-level source data (including Windsor's), just not broken back out by CMA in this particular publication.

Also worth noting for later: the **Notes** sheet lists 2021-Census-driven CMA boundary changes, two of which touch Windsor directly — *"Essex T: merged with Windsor CMA"* and *"Leamington MU: merged with Windsor CMA."* Relevant if a CMA-level table is pulled later and compared against older editions, since Windsor CMA's boundary isn't static across vintages.

## Dwelling types

Two different classification axes exist across the four data tables — worth keeping distinct, not conflating:

- **Tables C1 (quarterly) and C2 (cumulative/YTD)** — "Housing Starts by Dwelling Type" / "Cumulative Housing Starts by Dwelling Type" (per the Index sheet's own table titles). Dwelling-type columns: **Singles, Semis, Row, Apartment and Other, Total**.
- **Tables C3 (quarterly) and C4 (cumulative/YTD)** — "Housing Starts by Intended Market" / "Cumulative Housing Starts by Intended Market." This is a *different* axis (ownership intent, not structural type): **Homeownership, Rental, Condo, Co-op, Not Available, Total**.

Despite the similar-sounding titles, C1/C2 and C3/C4 are not the same breakdown of the same numbers — they're two independent cuts of starts activity. (This project's `etl/extract_cmhc_starts_completions.py` only extracts C1/C2, the dwelling-type cut — C3/C4 are profiled here but not yet in the ETL pipeline.)

## Monthly vs. annual series, and years covered

Neither. This edition is **quarterly** (Tables C1, C3 — "Second Quarter 2026") plus its own **cumulative year-to-date** figure (Tables C2, C4 — "January to June 2026"), not a monthly series and not a full annual series. The task's framing ("monthly vs. annual") doesn't match what this specific file actually contains — flagging that mismatch rather than forcing the data into the wrong description.

**Years covered: 2026 only**, and only one edition of it. This is a single point-in-time snapshot, not a multi-year historical series — there is no prior-quarter or prior-year data in this file to compare against. A real year-over-year supply story needs additional historical editions, which haven't been downloaded.

## Checking totals

Verified by direct computation against the real data, not assumed:

- **Tables C1/C2 (dwelling type):** for every (province × period × activity) combination, the four dwelling-type columns (Singles + Semis + Row + Apartment and Other) were summed and compared against that row's own Total column. **10/10 groups match exactly, 0 mismatches.**
- **Tables C3/C4 (intended market):** same check against the five intended-market columns (Homeownership + Rental + Condo + Co-op + Not Available). **55/55 rows match exactly, 0 mismatches**, with `-` (suppressed/not-applicable) cells correctly treated as 0 for the sum.

No arithmetic inconsistencies found anywhere in the workbook.

## Summary for the team

| Question | Answer |
|---|---|
| Windsor tables? | None exist in this file. Need a different, CMA-level CMHC table (proposal ref. [5]) to get Windsor specifically. |
| Dwelling types? | Singles, Semis, Row, Apartment and Other, Total (C1/C2) — distinct from the Intended Market axis in C3/C4. |
| Monthly or annual? | Neither — quarterly (C1/C3) + cumulative YTD (C2/C4), single 2026 edition. |
| Years covered? | 2026 only, one edition — not a historical series. |
| Totals check? | Clean. 10/10 (C1/C2) + 55/55 (C3/C4) rows reconcile exactly. |
