#!/usr/bin/env bash
dataOutput=/data

mkdir -p $dataOutput

python entrypoint.py admin_boundaries
python entrypoint.py buildings
