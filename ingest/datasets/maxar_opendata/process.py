"""Create STAC Collections and Items files."""

import json
import logging
import pystac
from os import makedirs, environ
import geopandas as gpd
from ..utils import run_cli, save_postgis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate(output_dir, limit):
    """Generate STAC Collections and Items files for Maxar Open Data."""
    logger.info("Connecting to static catalog...")
    makedirs(output_dir, exist_ok=True)
    catalog = pystac.Catalog.from_file(
        "https://maxar-opendata.s3.amazonaws.com/events/catalog.json"
    )

    collections = list(catalog.get_collections())
    logger.info(f"Found {len(collections)} collections")

    # loading only 3 collections for testing
    if limit:
        collections = collections[:limit]
    logger.info(f"Loading collections: {len(collections)}")

    logger.info("Creating collections.json file...")
    stac_collection_path = f"{output_dir}/collections.json"
    with open(stac_collection_path, "w") as f:
        for collection in collections:
            c = collection.to_dict()
            c["links"] = []
            c["id"] = "MAXAR_" + c["id"].replace("-", "_")
            c["description"] = "Maxar OpenData | " + c["description"]
            c["table"] = f"MAXAR_{c['id']}".replace("-", "_").lower()
            f.write(json.dumps(c) + "\n")
    # ##############
    # save collection stac
    # ##############
    output_json = run_cli(
        ["pypgstac", "load", "collections"],
        stac_collection_path,
        {"--method": "insert_ignore", "--dsn": environ["DATABASE_URL"]},
    )
    logger.info("Creating items .json files...")
    errors = []
    for collection in collections:
        collection_id = "MAXAR_" + collection.id.replace("-", "_")
        table = collection_id.lower()
        logger.info(f"Processing items for {collection_id}")
        file_path = f"{output_dir}/{collection_id}_items.json"

        features = []
        with open(file_path, "w") as f:
            # Each Collection has collections
            try:
                for c in collection.get_collections():
                    try:
                        # Loop through each items
                        # edit items and save into a top level collection JSON file
                        for item in c.get_all_items():
                            item_dict = item.make_asset_hrefs_absolute().to_dict()
                            item_dict["links"] = []
                            item_dict["collection"] = collection_id
                            item_dict["id"] = item.id.replace("/", "_")
                            features.append(item_dict)
                            item_str = json.dumps(item_dict)
                            f.write(item_str + "\n")
                    except Exception as e:
                        logger.info(f"Error: {e}")
                        errors.append(
                            {
                                "collection": collection_id,
                                "child_collection": c.id,
                                "error": e,
                            }
                        )
                        continue
            except Exception as e:
                logger.info(f"Error: {e}")
                errors.append(
                    {"collection": collection_id, "child_collection": None, "error": e}
                )
                continue
            else:
                output_json = run_cli(
                    ["pypgstac", "load", "items"],
                    file_path,
                    {"--method": "insert_ignore", "--dsn": environ["DATABASE_URL"]},
                )

        if features:
            # geojson_path = f"{output_dir}/{collection_id}_original.geojson"
            # json.dump(fc(features), open(geojson_path, "w"))
            gdf = gpd.GeoDataFrame.from_features(features)
            logger.info("Saving dataset in DB..")
            save_postgis(
                gdf=gdf,
                table_name=table,
                if_exists="replace",
                index=True,
                schema="pgstac",
                table_id="id",
            )

    if errors:
        logger.info(f"{len(errors)} errors occurred while processing items")
        logger.info(f"Errors: {errors}")
