# Live refresh demo (screen recording)

**What it shows:** the pipeline taking a newer government file all the way to the dashboards with one command, with the schema guard checking the file first. **Length:** about 5 minutes of recording.

**Why now works:** StatCan published **October 2026** housing starts and completions (table 34-10-0154-01), and the dashboards show data to **September 2026**. Checked on 19 November 2026 with `scheduled_refresh.py --check-only`, which downloaded the new file and passed the schema guard without loading anything. Running the refresh therefore moves Story 3 from *Jan-Sep 2026* to *Jan-Oct 2026* on screen.

> Record it only once: after the refresh the dashboards already show October, so a second run changes nothing visible. If you need to record again, restore the backup from step 1 first.

## Before recording (not on camera)

1. **Back up the local warehouse** (2 seconds; lets you undo the refresh):
   ```powershell
   docker exec -u postgres windsor_housing_postgres pg_dump -d housing_windsor --schema=warehouse --no-owner -Fc -f /tmp/before_refresh.dump
   ```
2. Close other programs: the load step needs memory. If it ever stops with `MemoryError`, stop Superset for the load (`docker stop windsor_housing_superset`), run the refresh, then `docker start windsor_housing_superset` and wait a minute.
3. Open three windows side by side:
   - PowerShell in the project folder;
   - the local Story 3 dashboard, tab **This Year So Far** (<http://localhost:8088/superset/dashboard/windsor-story-3/>), showing **Jan-Sep 2026: 690 starts, 1,029 completions**;
   - `logs/` in File Explorer (the run writes its log there).
4. Start the screen recorder (Windows: **Win + Alt + R** with Xbox Game Bar, or OBS).

## On camera

| Step | Do | Say (about) | You should see |
|---|---|---|---|
| 1 | Point at the tiles | "The dashboard shows housing starts to September 2026." | Jan-Sep 2026 Housing Starts **690** |
| 2 | Run `.venv\Scripts\python.exe etl\scheduled_refresh.py` | "One command downloads the newest StatCan tables, checks them, and rebuilds the warehouse." | `Downloaded data\raw\statcan\34100154-eng.zip` and the two rent and vacancy tables |
| 3 | Point at the guard output | "Before anything is loaded, the schema guard compares all 27 source files with their saved structure. A renamed column would stop the run here and the dashboards would keep the last good data." | `All 27 source files match the saved snapshot.` |
| 4 | Let it run (2-4 min) | "Each source is extracted to a tidy file, loaded, validated, and the 59 SQL views are rebuilt." | `=== extract_... ===` blocks, then `=== refresh_all.py ===`, then `Scheduled refresh finished` |
| 5 | Run `.venv\Scripts\python.exe etl\build_story3_dashboard.py` | "The dashboard builder refreshes the titles and notes from the new data." | `Dashboard ready: id=7`, and a NOTE that the intended-market files still cover Jan-Sep (they are downloaded by hand; this is the warning working) |
| 6 | Refresh the Story 3 tab in the browser | "The same dashboard now reads October." | **Jan-Oct 2026** in the tile titles, new totals, October in the shortfall and pipeline charts |
| 7 | Open the newest `logs/scheduled_refresh_*.log` | "Every run is logged; a failure also writes an alert and can post to Teams." | the full run |

## After recording

- **Keep the October data** (it is a real monthly update): rebuild the other dashboards and the website figures, then commit and deploy as usual:
  ```powershell
  .venv\Scripts\python.exe etl\build_all_dashboards.py
  .venv\Scripts\python.exe etl\export_site_highlights.py
  ```
  then the university steps in `docs/deploy_university.md` (export, load on whva, rebuild apss, publish the site).
- **Or undo it** (back to September):
  ```powershell
  docker exec -u postgres windsor_housing_postgres pg_restore -d housing_windsor --clean --if-exists --no-owner /tmp/before_refresh.dump
  ```
- Download the two year-to-date intended-market exports for October (`etl/README.md`, "Files downloaded by hand") so Story 3's intended-market chart matches the new month.
