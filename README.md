# visual-analytics-internship-project-2

COMP 8977 Internship/Project 2 – Visual Analytics on Open Data Sets Available from Canadian Government Sites

## Project

**Visual Analytics of Housing Affordability and Housing Market Trends in Windsor Using Canadian Open Data**

A public, web-based visual analytics platform for understanding housing affordability and housing-market conditions in the Windsor Census Metropolitan Area (CMA). The platform integrates official data from Statistics Canada and CMHC, stores it in a relational database, and presents it through interactive dashboards.

## Data Sources

- Statistics Canada — Census Profile, 2021 (98-401-X2021002)
- Statistics Canada — Shelter-cost-to-income ratio by tenure (98-10-0252-01)
- CMHC — Rental Market Survey Data Tables (Windsor, 2025)
- CMHC — Starts / Completions / Construction tables (2026 edition)
- CMHC — Rental Market Survey Data Tables (Canada, 2025, supporting/benchmarking)

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| Data sources | Statistics Canada, CMHC | Official census, affordability, rental-market and construction datasets |
| Data processing | Python (pandas, SQLAlchemy) | Profile, clean, reshape, validate and load source data |
| Database | PostgreSQL | Central store for cleaned tables, SQL views and analytical metrics |
| Analytics | Apache Superset | SQL exploration, KPIs, filters, charts and interactive dashboards |
| Front end | React | Public story pages, methodology/source pages and Superset integration |
| Containerisation | Docker | Consistent local setup of Superset and PostgreSQL |

**Project management:** Jira (sprint tracking), GitHub (version control), Microsoft Teams (communication)

## Team

| Member | Role |
|---|---|
| Dhritiben Patel | Project Manager & Data Analysis Lead |
| Romit Patel | Data Engineering Lead |
| Pavan Rella | Analytics & Visualisation Lead |
| Charmiben Patel | Front-end & Deployment Lead |

Supervisor: Dr. Andreas Maniatis · Course Instructor: Dr. Prashanth C. Ranga

See [docs/](docs/) for the full project proposal.
