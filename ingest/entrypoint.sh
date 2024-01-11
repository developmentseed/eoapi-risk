#!/usr/bin/env bash
dataOutput=/data

mkdir -p $dataOutput

python entrypoint.py population
python entrypoint.py admin_boundaries
python entrypoint.py health_facilities
python entrypoint.py buildings
