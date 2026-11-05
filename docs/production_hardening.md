# Production Hardening

How the hosted system is protected: HTTPS, secrets, daily database backups and firewall rules. The configuration lives in the repository so a deployment uses it unchanged; the server-specific steps at the end are run once on the host.

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
6. Load data with `etl/refresh_all.py`, then re-run `etl/enable_story1_embedding.py` so Superset allows the production origin.
7. Check: `https://<SITE_DOMAIN>` loads with a valid certificate, `http://` redirects to `https://`, the Story 1 embed works, `docker logs windsor_housing_db_backup` shows a backup, and `nc -zv <server> 5434` from another machine is refused.
