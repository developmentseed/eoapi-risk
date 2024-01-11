#!/usr/bin/env bash
set -x
export DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASS}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DBNAME}"
dataOutput=/data
mkdir -p $dataOutput
python entrypoint.py population
python entrypoint.py admin_boundaries
python entrypoint.py buildings
python entrypoint.py health_facilities
