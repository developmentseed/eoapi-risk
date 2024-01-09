#!/usr/bin/env bash
dataOutput=/data

for dataset_path in datasets/*; do
    if [ -d "$dataset_path" ]; then
        dataset=$(basename "$dataset_path")
        set -x
        mkdir -p $dataOutput
        python entrypoint.py "$dataset"
        cat $dataOutput/*.json > $dataOutput/items.json
        pypgstac load collections $dataOutput/collections.json --method insert_ignore
        pypgstac load items $dataOutput/items.json --method insert_ignore
        rm -rf $dataOutput/*
        set +x
    fi
done
