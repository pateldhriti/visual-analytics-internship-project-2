#!/bin/sh
# Runs automatically on first init of a fresh Postgres data directory
# (mounted to /docker-entrypoint-initdb.d/). Creates the separate database
# Superset uses for its own metadata, alongside the main housing data DB.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE "$SUPERSET_METADATA_DB";
EOSQL
