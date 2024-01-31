from tqdm import tqdm
import geopandas as gpd
from os import makedirs, environ
import logging
from joblib import Parallel, delayed
from ..utils import run_cli, save_postgis
import json
import os
import requests
import zipfile
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LINK = "https://earthquake.usgs.gov/product/shakemap/us6000lfn5/us/1703038955396/download/shape.zip"
basename_files = [
    "psa1p0",
    "mi",
    "pga",
    "pgv",
    "psa0p3",
    "psa3p0",
]

STAC_VERSION = "1.0.0"
COLLECTION = "earthquake_usgs_gov"
ITEM = f"{COLLECTION}_shakemap_afg"
TITLE = "Shakemap Peak Ground Acceleration, Afghanistan"
DESCRIPTION = "Shakemap  - M 6.3 - 34 km NNW of Herat, Afghanistan"
LICENSE = "Creative Commons Attribution International"
DATETIME = "2023-12-20"


def dowload_and_process(path_local):
    response = requests.get(LINK)
    zip_file_path = f"{path_local}/shapefiles.zip"
    with open(zip_file_path, "wb") as file:
        file.write(response.content)

    # Extract the ZIP file
    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
        zip_ref.extractall(f"{path_local}/shapefiles")

    # Read each shapefile into GeoPandas
    shapefile_dir = f"{path_local}/shapefiles"
    for filename in os.listdir(shapefile_dir):
        if filename.endswith(".shp"):
            file_basename, file_extension = os.path.splitext(filename)
            file_path = os.path.join(shapefile_dir, filename)
            gdf = gpd.read_file(file_path)
            logger.info(f"Loaded {filename} into GeoDataFrame:")
            logger.info("Saving dataset in DB...")
            gdf["id"] = gdf.index
            gdf.columns = [col.lower() for col in gdf.columns]
            gdf['area'] = gdf.area
            save_postgis(
                gdf=gdf,
                table_name=f"{ITEM}_{file_basename}",
                if_exists="replace",
                index=False,
                schema="public",
                table_id="id",
            )
            args = {
                "--id": f"{ITEM}_{file_basename}",
                "--datetime": DATETIME,
                "--collection": COLLECTION,
                "--asset-href": LINK,
            }
            # #################
            # save item stac
            # #################
            logger.info("Running fio stac for dataset...")
            output_json = run_cli(["fio", "stac"], file_path, args)
            output_json["output"]["title"] = TITLE
            output_json["output"]["description"] = DESCRIPTION
            output_json["output"]["license"] = LICENSE
            output_json["output"]["table"] = f"{ITEM}_{file_basename}"
            output_json["output"]["links"] = {
                "href": LINK,
                "rel": LINK,
                "title": TITLE,
            }
            stac_item_path = f"{file_path}_.json"
            with open(stac_item_path, "w") as file:
                file.write(json.dumps(output_json["output"]))

            #################
            # Run: pypgstac load collections
            #################
            logger.info("Importing item/colletion to pgstac...")
            output_json = run_cli(
                ["pypgstac", "load", "items"],
                stac_item_path,
                {"--method": "insert_ignore"},
            )


def run(path_local: str):
    #################
    # Load collection into the DB
    #################
    logger.info("\n\nLoad collection into the DB..")
    stac_collection_path = f"datasets/shakemap_peak/collection.json"
    run_cli(
        ["pypgstac", "load", "collections"],
        stac_collection_path,
        {"--method": "insert_ignore", "--dsn": environ["DATABASE_URL"]},
    )
    
    dowload_and_process(path_local)
