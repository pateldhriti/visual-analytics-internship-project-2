# Windsor Housing Visual Analytics

**COMP-8977 Internship/Project-2, Fall 2026 · University of Windsor**

A free, public tool that explains housing affordability and the housing market in the **Windsor Census Metropolitan Area** using official open data from Statistics Canada and CMHC. Five stories, each answering one question with interactive dashboards and a plain-language website:

| | Question | Answer in one line (data to October 2025) |
|---|---|---|
| **1** | Who faces the greatest affordability pressure? | Renters: 34.8% spend 30% or more of income on shelter, against 10.9% of owners. |
| **2** | What is happening in Windsor's rental market? | Apartment vacancy recovered from 1.8% (2022) to 3.7%, but the 2-bedroom rent rose 53% since 2019, to $1,454. |
| **3** | Is Windsor building enough housing? | Starts surged in 2024 and fell back; Windsor built 59% of the homes its 2016-2021 population growth needed. |
| **4** | How does Windsor compare to similar markets? | Still the cheapest of five Ontario cities ($1,454 for a 2-bedroom apartment), but since 2019 its rent rose 53%, more than London, Hamilton, Kitchener-Waterloo or Toronto. |
| **5** | **Combined Analysis:** how do affordability, rent and supply fit together? | About 6 in 10 Windsor renters cannot afford the average 2-bedroom: Windsor is cheaper, not more affordable. |

**Live (UWindsor campus or VPN):** website <https://whva.cs.uwindsor.ca> · dashboards <https://apss.cs.uwindsor.ca> (UWindsor login)

## How it works

```
Statistics Canada + CMHC files ─▶ Python ETL (checked, reshaped, validated) ─▶ PostgreSQL warehouse
   ─▶ 59 SQL views (every measure defined once) ─▶ Apache Superset dashboards  +  React website
```

- **27 source files**, each checked against its saved structure before anything is loaded; a weekly refresh downloads the tables that change.
- **A star-schema warehouse** of 8 dimensions and 9 fact tables; the dashboards and the website read the same views, so their numbers always agree.
- **Six dashboards** (Overview and Stories 1-5), each split into tabs that fit one screen.
- **Deployed on the University of Windsor's servers** with HTTPS, a firewall, daily backups and uptime monitoring.

Details: **[docs/architecture.md](docs/architecture.md)**.

## Get started

**New to the project? Follow [docs/setup_guide.md](docs/setup_guide.md)**: from an empty laptop to the running project in about two hours. In short:

```powershell
py -3.12 -m venv .venv; .venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env                                     # then fill in the passwords
cd docker; docker compose --env-file ../.env up -d; cd ..
.venv\Scripts\python.exe etl\fetch_raw_data.py              # plus 5 files saved by hand
.venv\Scripts\python.exe etl\scheduled_refresh.py --no-download
.venv\Scripts\python.exe etl\build_all_dashboards.py
cd web; npm install; npm run dev                            # http://localhost:5173
```

## Repository map

| Folder | Contents |
|---|---|
| `etl/` | The pipeline: `fetch_raw_data.py`, `schema_guard.py`, `extract_*.py`, `load_warehouse_facts.py`, `refresh_all.py`, `scheduled_refresh.py`; the dashboard builders `build_*_dashboard.py`; tests `test_*.py`. See [etl/README.md](etl/README.md). |
| `sql/` | Warehouse schema and the views of each story (`story1_views.sql` ... `story5_views.sql`) |
| `web/` | The React (Vite) website |
| `api/` | Guest-token API, used when the website embeds dashboards |
| `docker/` | Local PostgreSQL, Superset and Redis (`docker-compose.yml`), Superset settings |
| `deploy/` | University server configuration (`deploy/whva/`: nginx, firewall, backup, uptime check, restore test) and `load_test.py` |
| `docs/` | Design, data dictionary, decision log, story narratives, guides, reports |
| `data/` | `raw/` (downloads, not in git), `staging/` (extract output), `export/` (package for the university database) |
| `notebooks/` | Exploration notebooks from the first weeks |

## Documentation

| Document | For |
|---|---|
| [docs/setup_guide.md](docs/setup_guide.md) | installing and running the project |
| [docs/architecture.md](docs/architecture.md) | how the parts fit together |
| [docs/data_architecture.md](docs/data_architecture.md) | the database layers |
| [docs/data_dictionary.md](docs/data_dictionary.md) | every table and view |
| [etl/README.md](etl/README.md) | each pipeline script, the weekly refresh, files downloaded by hand |
| [docs/decision_log.md](docs/decision_log.md) | design and data decisions, with reasons |
| [docs/deploy_university.md](docs/deploy_university.md) | publishing to the university's servers |
| [docs/production_hardening.md](docs/production_hardening.md) | HTTPS, secrets, backups, firewall, uptime, restore test |
| [docs/design_document.md](docs/design_document.md) | the original design |
| `docs/story*_narrative_final.md` | the text of each story |

## Data sources

Statistics Canada: Census 2021 shelter cost by income and tenure (98-10-0252-01), Census Profile 2021 (98-401-X2021002), housing indicators by age (98-10-0241-01), starts and completions (34-10-0154-01), rents and vacancy (34-10-0133-01, 34-10-0130-01). CMHC: Rental Market Survey for Windsor (2021-2025), for Canada (2019-2025) and for the comparison cities; starts and completions by intended market (Housing Market Information Portal). All open data; see the website's Sources page and [docs/data_dictionary.md](docs/data_dictionary.md).

## Team

| Member | Role |
|---|---|
| Dhritiben Patel | Project Manager and Data Analysis Lead |
| Romit Patel | Data Engineering Lead |
| Pavan Rella | Analytics and Visualisation Lead |
| Charmiben Patel | Front-end and Deployment Lead |

Supervisor: Dr. Andreas Maniatis · Course Instructor: Dr. Prashanth C. Ranga
