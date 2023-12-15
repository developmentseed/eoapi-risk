#!/usr/bin/env bash

dataOutput=data
#create folder
mkdir -p $dataOutput

# run script

python src/run.py --iso3_country=GBR \
  --iso3_country=PER \
  --save_local \
  --path_local=$dataOutput

