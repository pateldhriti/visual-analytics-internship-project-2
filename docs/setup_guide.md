# Setup guide: from an empty laptop to the running project

For a new student taking over the project. It takes about **2 hours**, most of it downloads. Written for Windows (the team's machines); on macOS or Linux use `.venv/bin/python` and forward slashes. Every command runs from the project folder unless it says otherwise. If a step fails, see [Troubleshooting](#troubleshooting) at the end.

## 1. Install the tools

| Tool | Version | Check |
|---|---|---|
| Git | any recent | `git --version` |
| Python | **3.12** (3.11 also works; 3.13 does not yet suit every library) | `py -3.12 --version` |
| Node.js | 20 or newer | `node --version` |
| Docker Desktop | any recent, running | `docker info` |
| GitHub CLI (optional, for pull requests) | any | `gh --version` |

Docker needs about **8 GB** of free memory for PostgreSQL, Superset and Redis together; close other programs when loading data.

## 2. Get the code and the Python environment

```powershell
git clone https://github.com/pateldhriti/visual-analytics-internship-project-2.git
cd visual-analytics-internship-project-2
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\pre-commit.exe install          # checks run on every commit
cd web; npm install; cd ..
```

## 3. Settings

```powershell
copy .env.example .env
```

Edit `.env` and fill in at least:

| Setting | What to put |
|---|---|
| `POSTGRES_PASSWORD` | any password for your local database |
| `SUPERSET_SECRET_KEY`, `GUEST_TOKEN_JWT_SECRET` | random strings: `.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(42))"` |
| `SUPERSET_ADMIN_USER`, `SUPERSET_ADMIN_PASSWORD` | the login you want for your local Superset |

Leave the other settings as they are. `.env` is ignored by git: never commit it, and never put a password in any other file.

## 4. Start PostgreSQL, Superset and Redis

```powershell
cd docker
docker compose --env-file ../.env up -d
cd ..
docker ps            # windsor_housing_postgres, windsor_housing_superset, windsor_housing_redis: "healthy" after 1-3 minutes
```

Superset is then at <http://localhost:8088> (log in with your `SUPERSET_ADMIN_*` values). The first start runs Superset's setup and takes a few minutes.

## 5. Get the data

```powershell
.venv\Scripts\python.exe etl\fetch_raw_data.py
```

This downloads 22 files into `data/raw/` (about 1.5 GB, mostly the StatCan Census tables) and lists **5 files that must be saved by hand**, with where to get each. [etl/README.md](../etl/README.md), section "Files downloaded by hand", explains each one step by step (the Census Profile, CMHC's quarterly workbook, and three exports from CMHC's Housing Market Information Portal). Run `fetch_raw_data.py --check` to see which files are still missing.

## 6. Build the warehouse

One command checks every file, extracts it and loads the database:

```powershell
.venv\Scripts\python.exe etl\scheduled_refresh.py --no-download
```

It prints each step; the end should read `Scheduled refresh finished`. It runs, in order: the schema guard (all 27 files must match their saved structure), every `extract_*.py`, then `refresh_all.py` (warehouse schema, fact tables, Story 1's tables, the 59 views, and the Superset datasets). If it stops at the schema guard, a source file changed: see [etl/README.md](../etl/README.md), "Weekly scheduled refresh and schema guard".

## 7. Build the dashboards

```powershell
.venv\Scripts\python.exe etl\build_all_dashboards.py
```

This creates the six dashboards in your local Superset (about 5 minutes). Check <http://localhost:8088/dashboard/list/>: Overview and Stories 1-5, each with tabs.

## 8. Run the website

```powershell
.venv\Scripts\python.exe etl\export_site_highlights.py      # the site's figures, from the same views
.venv\Scripts\python.exe api\guest_token_server.py           # in a second window: lets the site embed dashboards
cd web; npm run dev
```

Open <http://localhost:5173>. Each story page shows its narrative, its key findings and its dashboard.

## 9. Check everything works

```powershell
.venv\Scripts\python.exe -m pytest etl api -q      # 115 tests, all should pass
cd web; npm run lint; npm run build; cd ..
.venv\Scripts\python.exe etl\schema_guard.py       # "Schema guard passed: 27 source files ..."
```

The same tests run on GitHub for every merge to `main`.

## 10. How the team works

- **One branch per piece of work**, a pull request, then a merge to `main`; never push unrelated work straight to `main`, and never delete branches.
- **Dashboards are built by script**, never edited by hand in Superset: a rebuild would overwrite manual changes. Change the `etl/build_*_dashboard.py` file and rerun it.
- **Measures live in the SQL views** (`sql/story*_views.sql`). After changing a view: `etl\apply_sql_views.py`, then rebuild the dashboard, then `etl\export_site_highlights.py`.
- Record design and data decisions in [decision_log.md](decision_log.md), and new tables or views in [data_dictionary.md](data_dictionary.md).

## 11. Publishing to the university's servers

Production runs on the University of Windsor's servers (on campus or the GlobalProtect VPN): the database `whva`, Superset at apss, and the website on whva. The steps (export the data package, load it on whva, build the dashboards with `--env .env.apss`, build and copy the website) are in [deploy_university.md](deploy_university.md). Ask the project manager for access to whva and apss.

## Where to read next

| To understand | Read |
|---|---|
| how the parts fit | [architecture.md](architecture.md) |
| the database layers | [data_architecture.md](data_architecture.md) |
| every table and view | [data_dictionary.md](data_dictionary.md) |
| each pipeline script | [etl/README.md](../etl/README.md) |
| why things are the way they are | [decision_log.md](decision_log.md) |
| servers, backups, monitoring | [production_hardening.md](production_hardening.md) |

## Troubleshooting

| Problem | Fix |
|---|---|
| `MemoryError` or "Memory allocation failed" while loading | Close other programs. If it persists, stop Superset for the load (`docker stop windsor_housing_superset`), run step 6 again, then `docker start windsor_housing_superset`. |
| Superset login page does not load | Wait 2-3 minutes after the first start; `docker logs windsor_housing_superset` shows progress. |
| `failed to connect to the docker API` | Docker Desktop is not running: start it and wait until `docker info` works. |
| Schema guard fails | A source file changed its columns or sheets. Compare the file with the message; if the change is real and expected, update the extract, then `etl\schema_guard.py --update`. |
| A dashboard chart shows "Columns missing in dataset" | The view's columns changed: refresh the dataset in Superset (Datasets, the dataset, "Sync columns from source") or rerun `etl\register_superset_datasets.py`, then rebuild the dashboard. |
| `fetch_raw_data.py` fails on the Census Profile | That site refuses scripted downloads: save it by hand (step 5). |
| Website shows old numbers | Rerun `etl\export_site_highlights.py` and reload the page. |
