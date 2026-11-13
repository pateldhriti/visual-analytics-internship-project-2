# Production Hardening

How the hosted system is protected: HTTPS, secrets, daily database backups and firewall rules. The configuration lives in the repository so a deployment uses it unchanged; the server-specific steps are run once on the host.

**The project now runs on the university's servers** (decision D46): the data in PostgreSQL `whva`, the dashboards on apss, the website on whva. Section 6 covers that setup. Sections 1-5 describe our own Docker stack (Caddy, Postgres, Superset), which stays the fallback if apss cannot serve the dashboards publicly.

| Area | What is in place | Files |
|---|---|---|
| HTTPS | Caddy reverse proxy with automatic Let's Encrypt certificates, HTTP→HTTPS redirect and HSTS; Superset trusts the proxy and uses secure cookies | `docker/Caddyfile`, `docker/docker-compose.prod.yml`, `docker/superset_config.py` |
| Secrets | All passwords and keys come from environment variables in `.env` (git-ignored); Superset refuses to start without them | `.env.example`, `docker/superset_config.py` |
| Backups | Daily `pg_dump` of both databases, 14 days kept, tested restore | `docker/backup.sh`, `docker/docker-compose.prod.yml` |
| Firewall | Only ports 22, 80 and 443 open; Postgres, Redis, Superset and the token API are not reachable from outside | `docker/docker-compose.yml`, host `ufw` rules below |

---

## 1. HTTPS

**How it works.** `docker/docker-compose.prod.yml` adds a Caddy container that is the only service with public ports (80 and 443). For each domain in `docker/Caddyfile`, Caddy requests a certificate from Let's Encrypt, renews it automatically before it expires and redirects plain HTTP to HTTPS.

| Domain (from `.env`) | Serves |
|---|---|
| `SITE_DOMAIN` | The React build (`web/dist`), plus `/api/*` forwarded to the guest-token API |
| `SUPERSET_DOMAIN` | Apache Superset |

Every response carries `Strict-Transport-Security` (browsers then refuse plain HTTP for a year), `X-Content-Type-Options: nosniff` and a strict referrer policy, and the `Server` header is removed.

**Superset behind the proxy.** The production file sets `SUPERSET_HTTPS=true`, which makes `docker/superset_config.py`:

- trust the proxy's `X-Forwarded-*` headers (`ENABLE_PROXY_FIX`), so links Superset generates use `https://`;
- send the session cookie only over HTTPS (`SESSION_COOKIE_SECURE`), never to JavaScript (`SESSION_COOKIE_HTTPONLY`), and with `SameSite=None` so the dashboard embedded on the website keeps working;
- allow framing only by the origins in `FRONTEND_ORIGINS`.

Locally `SUPERSET_HTTPS` is unset, so development on `http://localhost` behaves as before.

**On Render** (the hosting choice in `docs/hosting_decision.md`), Render terminates HTTPS for each service itself, so Caddy is not needed there: set `SUPERSET_HTTPS=true` and `FRONTEND_ORIGINS=https://<site>` on the Superset service.

## 2. Secrets in environment variables

No secret is in the code or in git. Each one is read from the environment, which Docker Compose fills from `.env`; `.env` is listed in `.gitignore`, and `.env.example` documents every name with an empty value.

| Variable | Used by | How to generate |
|---|---|---|
| `POSTGRES_PASSWORD` | Postgres, Superset, ETL, backups | `python -c "import secrets; print(secrets.token_urlsafe(24))"` |
| `SUPERSET_SECRET_KEY` | Signs Superset sessions | `python -c "import secrets; print(secrets.token_urlsafe(42))"` |
| `GUEST_TOKEN_JWT_SECRET` | Signs embedded-dashboard guest tokens | same as above |
| `SUPERSET_ADMIN_PASSWORD` | Superset admin login; the token API logs in with it | `python -c "import secrets; print(secrets.token_urlsafe(16))"` |

Rules:

- `docker/superset_config.py` reads `SUPERSET_SECRET_KEY`, `GUEST_TOKEN_JWT_SECRET` and the database password with `os.environ[...]`, so Superset fails to start if one is missing instead of running with an unsafe default.
- Use **different values in production** from anyone's local `.env`. On the server, create `.env` with `chmod 600 .env` so only the deploying user can read it.
- On Render, enter the same names under each service's *Environment* settings instead of uploading a file.
- **Rotation:** change the value in `.env` and restart the affected containers (`docker compose ... up -d`). Changing `SUPERSET_SECRET_KEY` logs everyone out; changing `GUEST_TOKEN_JWT_SECRET` invalidates tokens already issued (the website requests new ones automatically).
- A repository scan for hard-coded passwords, keys and tokens found none (5 November 2026).

## 3. Daily database backups

**Schedule.** The `db-backup` service in `docker/docker-compose.prod.yml` runs `docker/backup.sh` when it starts and then every 24 hours.

**What is backed up.** Both databases: `housing_windsor` (project data) and `superset_meta` (dashboards, charts, users). Each becomes one compressed `pg_dump` custom-format file named `<database>_<UTC time>.dump`. Backups older than `BACKUP_RETENTION_DAYS` (default 14) are deleted.

**What is skipped.** The *rows* of the `raw` and `staging` schemas. `raw` is an exact copy of the government files in `data/raw`, and `staging` holds intermediate ETL output; `etl/refresh_all.py` rebuilds both. They are 3.6 GB of the 3.7 GB database, so skipping them keeps a backup to about 2–3 MB while keeping everything that cannot be regenerated. Their table definitions are still included. Set `BACKUP_SKIP_DATA=""` to back up everything.

**Where backups live.** In the Docker volume `dbbackups`, not in a project folder. (During testing on Windows, writing large dumps into the OneDrive-synced project folder crashed Docker Desktop.) A backup on the same server does not survive the server being lost, so copy them off regularly:

```bash
docker cp windsor_housing_db_backup:/backups ./backups-$(date +%F)
```

`backups/` is git-ignored so a local copy is never committed.

**Run a backup now:**

```bash
docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
    run --rm --no-deps --entrypoint sh db-backup /usr/local/bin/backup.sh
```

**Restore** (into a new database first, check it, then swap):

```bash
docker exec -it windsor_housing_postgres createdb -U "$POSTGRES_USER" housing_windsor_restored
docker cp housing_windsor_<time>.dump windsor_housing_postgres:/tmp/restore.dump
docker exec -it windsor_housing_postgres pg_restore -U "$POSTGRES_USER" --no-owner \
    --dbname=housing_windsor_restored /tmp/restore.dump
# then re-run etl/refresh_all.py if the raw/staging rows are needed
```

**Tested 5 November 2026** against the local database: `housing_windsor` backed up to 2.3 MB and `superset_meta` to 612 KB; the dump was restored into a temporary database, which had the same row counts as the live one (90,720 shelter-cost rows, 2,385 rental-market rows) and working views. The temporary database was then dropped.

## 4. Firewall rules

**Inside Docker.** Only Caddy publishes ports to the outside (80, 443). In `docker/docker-compose.yml`, Postgres and Superset publish their ports on `BIND_ADDRESS`, which defaults to `127.0.0.1` (this machine only). Redis and the token API publish no ports at all; Caddy and Superset reach them over Docker's internal network.

This matters because Docker writes its own firewall rules when it publishes a port, **bypassing `ufw`**: a port published on `0.0.0.0` would be open to the internet even with `ufw` set to deny it. Binding to `127.0.0.1` is what actually keeps the database private. Do not change `BIND_ADDRESS` on a server.

**On the host (Ubuntu with `ufw`), run once:**

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from <admin-ip-or-campus-range> to any port 22 proto tcp   # SSH, restricted
sudo ufw allow 80/tcp     # Let's Encrypt challenge + redirect to HTTPS
sudo ufw allow 443/tcp    # HTTPS
sudo ufw allow 443/udp    # HTTP/3
sudo ufw enable
sudo ufw status verbose
```

To reach Postgres or Superset's port 8088 for maintenance, use an SSH tunnel (`ssh -L 5434:127.0.0.1:5434 user@server`) instead of opening a port.

**On Render**, there is no host firewall to manage: keep Postgres as a private service (no public connection string shared) and expose only the website and Superset web services.

## 5. Deployment checklist

1. Point `SITE_DOMAIN` and `SUPERSET_DOMAIN` DNS A records at the server.
2. Create `.env` from `.env.example` with new production secrets, `FRONTEND_ORIGINS=https://<SITE_DOMAIN>`, the two domains and `ACME_EMAIL`; `chmod 600 .env`.
3. Apply the `ufw` rules in section 4.
4. Build the website: `cd web && npm ci && npm run build`.
5. Start everything:
   `docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d`
6. Load data with `etl/refresh_all.py`, then re-run `etl/enable_dashboard_embedding.py` so Superset allows the production origin for all six dashboards.
7. Check: `https://<SITE_DOMAIN>` loads with a valid certificate, `http://` redirects to `https://`, the Story 1 embed works, `docker logs windsor_housing_db_backup` shows a backup, and `nc -zv <server> 5434` from another machine is refused.

---

## 6. On the university's servers (current deployment)

Who runs what:

| Service | Run by | HTTPS | Backups | Firewall |
|---|---|---|---|---|
| PostgreSQL `whva` (psql.cs.uwindsor.ca) | University IT | IT | IT, plus our daily schema backup below | IT: only campus hosts may connect (our laptops on the VPN are refused) |
| Superset 6 (apss.cs.uwindsor.ca) | University IT | IT | IT | IT |
| whva.cs.uwindsor.ca (website, token API) | Us (sudo) | Our nginx with the university's certificate | Nothing to back up: the site is rebuilt from git | Our nftables rules below |

The files are in `deploy/whva/`, checked before commit: nginx `-t` with a test certificate, `nft -c` and `systemd-analyze verify` on Debian 13. The backup script was also run, restored and pruned against a copy of our database.

### 6.1 HTTPS

The university issued a certificate for whva (`/etc/ssl/certs/whva/fullchain.pem` and `privkey.pem`, valid until 1 February 2027; IT renews it). `deploy/whva/nginx-whva.conf`:

- redirects HTTP to HTTPS;
- allows only TLS 1.2 and 1.3;
- sends HSTS, `nosniff`, a strict referrer policy and `frame-ancestors 'self'`, and hides the nginx version;
- serves the React build from `/var/www/whva`;
- forwards `/api/` to the token API on `127.0.0.1:8090`.

Install, once nginx is approved:

```bash
sudo apt install nginx
sudo cp nginx-whva.conf /etc/nginx/sites-available/whva
sudo ln -s /etc/nginx/sites-available/whva /etc/nginx/sites-enabled/whva
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Check: `curl -I http://whva.cs.uwindsor.ca` returns `301` to `https://`, and the browser shows a valid certificate. Before 1 February 2027, confirm with IT that the renewed certificate is placed at the same paths, then `sudo systemctl reload nginx`.

### 6.2 Secrets

No secret is in git or on a command line:

| Secret | Where it lives | Protection |
|---|---|---|
| University password, for building dashboards | `.env.apss` on the laptop (git-ignored by `.env.*`) | Only on the laptop of the person building |
| Database password, for backups | `~/.pgpass` on whva | `chmod 600`; read by `pg_dump` |
| Token API's Superset login | `/etc/whva/token-api.env` (template `deploy/whva/token-api.env.example`) | root-owned, `chmod 600`, passed by systemd as environment variables |

The token API runs as its own system user `whva-api`, with systemd's sandboxing options (`deploy/whva/whva-token-api.service`). It logs in to apss through LDAP (`SUPERSET_LOGIN_PROVIDER=ldap`), because apss has no login form. Issuing guest tokens on apss also needs the `can_grant_guest_token` permission and embedding enabled on our dashboards; only the admin can grant those. Until then, the website links to the dashboards instead of embedding them.

```bash
sudo useradd --system --home /opt/whva --shell /usr/sbin/nologin whva-api
sudo install -d -m 755 /opt/whva && sudo install -d -m 700 /etc/whva
sudo install -m 600 token-api.env.example /etc/whva/token-api.env
sudoedit /etc/whva/token-api.env
# copy the project to /opt/whva/app; create /opt/whva/venv (needs python3-venv) and install requirements.txt
sudo cp whva-token-api.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now whva-token-api
curl -s http://127.0.0.1:8090/api/health
```

### 6.3 Daily database backup

IT backs up the database server. We also keep our own daily copy of our schema, so we can undo a bad load ourselves. `deploy/whva/backup_whva_warehouse.sh`:

- `pg_dump`s the `warehouse` schema of `whva`, compressed (custom format, about 1.2 MB);
- checks that the file can be read back before keeping it;
- deletes copies older than 14 days.

The timer runs it every day at 03:30 and catches up after downtime. No new packages are needed: whva already has the PostgreSQL client. This part can be installed now.

```bash
# on whva, in your home directory
mkdir -p ~/whva && cp backup_whva_warehouse.sh ~/whva/ && chmod 700 ~/whva/backup_whva_warehouse.sh
printf 'psql.cs.uwindsor.ca:5432:whva:%s:<password>\n' "$USER" > ~/.pgpass   # replace <password> in an editor
chmod 600 ~/.pgpass
~/whva/backup_whva_warehouse.sh                       # first backup now; prints "backup ok"
mkdir -p ~/.config/systemd/user
cp whva-backup.service whva-backup.timer ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now whva-backup.timer
sudo loginctl enable-linger "$USER"                   # run the timer while you are logged out
systemctl --user list-timers whva-backup.timer
```

To restore a backup (it replaces our schema only):

```bash
pg_restore -h psql.cs.uwindsor.ca -U "$USER" -d whva --clean --if-exists --no-owner ~/backups/whva_warehouse_<time>.dump
```

For a planned data refresh, the export package (`docs/deploy_university.md`, part 1) is still the way to load data. The backup is for undoing mistakes.

### 6.4 Firewall

`deploy/whva/nftables-whva.conf` drops all incoming traffic except SSH (22), HTTP (80) and HTTPS (443). It allows loopback, replies and ping. Outgoing traffic is not restricted, because whva must reach PostgreSQL, apss and Debian's updates. The token API listens only on `127.0.0.1`, so it cannot be reached from outside even without the firewall.

IT may already filter traffic to whva, and a firewall mistake can lock us out of SSH. **Ask the admin before enabling it**, and apply it with an automatic rollback:

```bash
sudo apt install nftables
sudo cp /etc/nftables.conf /etc/nftables.conf.bak   # Debian's default: allows everything
sudo nft -c -f nftables-whva.conf                   # syntax check
sudo systemd-run --on-active=180 --unit=fw-rollback nft -f /etc/nftables.conf.bak   # undo in 3 minutes
sudo nft -f nftables-whva.conf
# within 3 minutes, from a NEW terminal: ssh in again and open the website. If both work, keep the rules:
sudo systemctl stop fw-rollback.timer
sudo cp nftables-whva.conf /etc/nftables.conf && sudo systemctl enable nftables
sudo nft list ruleset
```
