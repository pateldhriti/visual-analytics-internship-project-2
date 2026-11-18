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

Live at <https://whva.cs.uwindsor.ca> since 18 November 2026, served by
nginx over HTTPS with the university's certificate. Like apss, it can only
be reached on the UWindsor network or through the VPN.

### Dashboards: links for now, embedded later

apss does not yet let other sites embed its dashboards: it sends
`X-Frame-Options: SAMEORIGIN`, and our Alpha account can neither enable
embedding on a dashboard nor issue guest tokens. These changes have been
requested from the admin. Until they are made, the site is built in
**link mode**: each story page shows a card with an **Open the dashboard**
button that opens it on apss (UWindsor login). Everything else on the site
(text, KPI tiles, the site's own charts) is the same as locally.

### Build (laptop, PowerShell, project folder)

```powershell
cd web
$env:VITE_SUPERSET_URL = "https://apss.cs.uwindsor.ca"
$env:VITE_EMBED_MODE = "link"     # leave this out once apss allows embedding
npm run build
Remove-Item Env:VITE_SUPERSET_URL, Env:VITE_EMBED_MODE
cd ..
scp -r web\dist <username>@whva.cs.uwindsor.ca:~/
```

### Publish (on whva)

```bash
sudo rm -rf /var/www/whva/*
sudo cp -r ~/dist/. /var/www/whva/
sudo chmod -R a+rX /var/www/whva    # scp from Windows makes the folders owner-only; nginx must read them
```

No restart is needed. Check from the laptop: <https://whva.cs.uwindsor.ca>
loads with a padlock, and `http://` redirects to `https://`.

### First-time setup (done once, 18 November 2026)

```bash
sudo apt update && sudo apt install -y nginx
sudo cp ~/nginx-whva.conf /etc/nginx/sites-available/whva      # deploy/whva/nginx-whva.conf
sudo ln -s /etc/nginx/sites-available/whva /etc/nginx/sites-enabled/whva
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Then publish as above. Security settings (headers, TLS versions), the
daily backup and the optional firewall are in
`docs/production_hardening.md`, section 6. When the admin enables
embedding, also install the guest-token API (section 6.2) and rebuild
without `VITE_EMBED_MODE`.
