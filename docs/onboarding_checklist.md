# Laptop Onboarding Checklist

For getting a new team laptop (Romit, Pavan, Charmiben) running against this repo. Each person runs this on their own machine — it can't be done remotely for them.

## 1. Clone and branch

- [ ] `git clone https://github.com/pateldhriti/visual-analytics-internship-project-2.git`
- [ ] Confirm you're on `main`: `git branch --show-current`
- [ ] Follow the team's git workflow: always branch before pushing unrelated work, raise a PR and merge through GitHub rather than pushing to `main` directly (now enforced by branch protection — direct pushes to `main` are rejected by GitHub itself).

## 2. Python environment

Follow **[README.md § Development Environment Setup](../README.md#development-environment-setup)** steps 1–6 — venv on Python 3.12, `pip install -r requirements.txt`, Jupyter kernel registration, and `pre-commit install` (step 6 — don't skip this one, it's new).

- [ ] `.venv` created and activated
- [ ] `pip install -r requirements.txt` completed with no errors
- [ ] Jupyter kernel registered (`windsor-housing` / "Windsor Housing Analytics")
- [ ] `pre-commit install` run — verify with `pre-commit run --all-files` (should pass clean)

## 3. Local secrets

- [ ] Copy `.env.example` to `.env`
- [ ] Fill in a local `POSTGRES_PASSWORD` (any value for local dev)
- [ ] Generate `SUPERSET_SECRET_KEY` and `SUPERSET_ADMIN_PASSWORD`: `python -c "import secrets; print(secrets.token_urlsafe(42))"`
- [ ] Confirm `.env` is **not** tracked by git: `git status` should not list it

## 4. Docker stack (optional unless working on data/dashboard tasks)

Follow **[README.md § Running the full stack](../README.md#running-the-full-stack-postgresql--redis--superset)**.

- [ ] Docker Desktop installed and running
- [ ] `docker compose --env-file ../.env up -d` from `docker/` starts Postgres, Redis, Superset without errors
- [ ] `http://localhost:8088` reachable, logs in with your own `.env` admin credentials

## 5. Verify

- [ ] Run `notebooks/00_environment_check.ipynb` top to bottom — all imports succeed
- [ ] Make a trivial commit (e.g., whitespace fix) on a throwaway branch and confirm the pre-commit hook actually runs
- [ ] Confirm `git push` to `main` directly is rejected (branch protection working) — try `git push origin HEAD:main` and expect it to fail

## What branch protection now enforces (as of this setup)

- No direct pushes to `main` — every change goes through a PR
- No force-pushes to `main`
- `main` cannot be deleted

The repo owner (admin) can still merge PRs without a separate required review — this project's size doesn't need multi-approver gating yet, just the "no accidental direct push" guardrail.
