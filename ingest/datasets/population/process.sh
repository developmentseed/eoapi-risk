#!/usr/bin/env bash

dataOutput=data
#create folder
mkdir -p $dataOutput

# run script

python src/run.py --path_local=$dataOutput

