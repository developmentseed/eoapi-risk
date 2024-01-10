"""Create STAC Collections and Items files."""

import json
import logging
import pathlib
import pystac
from os import makedirs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate(output_dir="."):
    """Generate STAC Collections and Items files for Maxar Open Data."""
    logger.info("Connecting to static catalog...")
    makedirs(output_dir, exist_ok=True)
    catalog = pystac.Catalog.from_file(
        "https://maxar-opendata.s3.amazonaws.com/events/catalog.json"
    )

    collections = list(catalog.get_collections())
    logger.info(f"Found {len(collections)} collections")
    logger.info(collections)

    # loading only 3 collections for testing
    collections = collections[:3]
    logger.info(f"Loading collections: {collections}")

    logger.info("Creating collections.json file...")
    with open(pathlib.Path(output_dir) / "collections.json", "w") as f:
        for collection in collections:
            c = collection.to_dict()
            c["links"] = []
            c["id"] = "MAXAR_" + c["id"].replace("-", "_")
            c["description"] = "Maxar OpenData | " + c["description"]
            f.write(json.dumps(c) + "\n")

    logger.info("Creating items .json files...")
    errors = []
    for collection in collections:
        collection_id = "MAXAR_" + collection.id.replace("-", "_")
        logger.info(f"Processing items for {collection_id}")
        with open(pathlib.Path(output_dir) / f"{collection_id}_items.json", "w") as f:
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
    if errors:
        logger.info(f"{len(errors)} errors occurred while processing items")
        logger.info(f"Errors: {errors}")
