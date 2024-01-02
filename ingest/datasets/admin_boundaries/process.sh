#!/usr/bin/env bash

dataOutput=data
#create folder
mkdir -p $dataOutput

# run script

python src/run.py --iso3_country=AFG \
  --save_local \
  --path_local=$dataOutput
