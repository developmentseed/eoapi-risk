#!/usr/bin/env bash
set -x
export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASS}@${PGHOST}:${PGPORT}/${POSTGRES_DBNAME}"
dataOutput=/data
mkdir -p $dataOutput
python entrypoint.py population
python entrypoint.py admin_boundaries
python entrypoint.py buildings
python entrypoint.py health_facilities
python entrypoint.py maxar_opendata
python entrypoint.py shakemap_peak