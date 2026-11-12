# Moving the dashboards to the university's servers

The university provides three services (connect GlobalProtect first):

| Service | Address | What we use it for |
|---|---|---|
| PostgreSQL 15 | `psql.cs.uwindsor.ca`, database `whva` | the data the dashboards read (schema `warehouse`) |
| Superset 6 | <https://apss.cs.uwindsor.ca> | the dashboards; connection `psql_ss_whva` (created by the admin) points at `whva` |
| whva | `whva.cs.uwindsor.ca` (SSH, sudo) | the website and the token API (part 3) |

Our laptops cannot connect to PostgreSQL directly (its access rules refuse
VPN addresses), but whva can, so the data is loaded from whva. Logins are
your university username and password everywhere.

## 1. Load the data into `whva`

On your laptop, in the project folder (PowerShell):

```powershell
.venv\Scripts\python.exe etl\export_for_shared_db.py
scp data\export\whva_warehouse.sql.gz <username>@whva.cs.uwindsor.ca:~
ssh <username>@whva.cs.uwindsor.ca
```

Then on whva:

```bash
gunzip -c whva_warehouse.sql.gz | psql -h psql.cs.uwindsor.ca -U <username> -d whva -v ON_ERROR_STOP=1 -1 -q > /dev/null && echo LOADED
psql -h psql.cs.uwindsor.ca -U <username> -d whva -c "SELECT count(*) AS cities FROM warehouse.v_story5_city_profile"
```

`LOADED` and `cities = 5` mean it worked. The file (about 2 MB) replaces the
whole `warehouse` schema each time, so after a data refresh you repeat this
part unchanged. It touches nothing outside our schema.

## 2. Build the dashboards on apss

On your laptop, create `.env.apss` in the project folder (git ignores it):

```
SUPERSET_URL=https://apss.cs.uwindsor.ca
SUPERSET_TARGET=shared
SUPERSET_DATABASE_NAME=psql_ss_whva
SUPERSET_LOGIN_USER=<username>
SUPERSET_LOGIN_PASSWORD=<password>
```

Then:

```powershell
.venv\Scripts\python.exe etl\build_all_dashboards.py --env .env.apss
```

It registers the datasets on `psql_ss_whva` and builds all six dashboards,
each named "Windsor Housing | ..." so nothing can clash with other teams'
work. Re-run it after any change to the dashboard scripts; it updates the
dashboards in place.

## 3. The website on whva

Waiting for the admin's answer on installing nginx and python3-venv and on
public dashboard access; this part will be filled in then.
