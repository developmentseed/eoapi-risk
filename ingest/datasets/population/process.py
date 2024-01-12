from os import makedirs, environ
import geopandas as gpd
import logging
import requests
import re
from tqdm import tqdm
import gzip
import shutil
import json
from ..utils import run_cli, save_postgis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PAGE_LINK = "https://data.humdata.org/dataset/kontur-population-afghanistan"
REGEX_URL = r'<a\s+(?:[^>]*?\s+)?href="(http[s]?://[^"]*)"'
STAC_VERSION = "1.0.0"
COLLECTION = "population_hexbins"
ITEM = f"{COLLECTION}_afghanistan"
TITLE = "Afghanistan, Population Density for 400m H3 Hexagons"
DESCRIPTION = "Built from Kontur Population, Global Population Density for 400m H3 Hexagons Vector H3 hexagons with population counts at 400m resolution"
LICENSE = "Creative Commons Attribution International"
DATETIME = "2022-06-30"


def get_link():
    r = requests.get(PAGE_LINK)
    all_links = re.findall(REGEX_URL, r.text)
    filter_links = [i for i in all_links if ".gpkg.gz" in i]
    return filter_links[-1]


def download_data(link, file_tmp_path):
    file_gpkg = file_tmp_path[:-3]
    block_size = 1024
    response = requests.get(link, stream=True)

    total_size_in_bytes = int(response.headers.get("content-length", 0))
    # create folter
    with open(file_tmp_path, "wb") as file, tqdm(
        desc=file_tmp_path,
        total=total_size_in_bytes,
        unit="iB",
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(block_size):
            bar.update(len(data))
            file.write(data)

    with gzip.open(file_tmp_path, "rb") as f_in:
        with open(file_gpkg, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    return file_gpkg


def run(path_local):
    #################
    # Load collection into the DB
    #################
    # logger.info("\n\nLoad collection into the DB..")
    # stac_collection_path = f"datasets/population/collection.json"
    # logger.info("Importing colletion to pgstac...")
    # output_json = run_cli(
    #     ["pypgstac", "load", "collections"],
    #     stac_collection_path,
    #     {"--method": "insert_ignore", "--dsn": environ["DATABASE_URL"]},
    # )
    # #################
    # Read and Save geo data in the DB
    # #################
    # logger.info("\n\nRead and Save geo data in the DB...")
    link = get_link()
    # makedirs(path_local, exist_ok=True)
    # file_name = link.split("/")[-1]
    # file_gpkg = download_data(link, f"{path_local}/{file_name}")
    # gdf = gpd.read_file(file_gpkg)
    # gdf = gdf.to_crs(4326)
    # gdf["id"] = gdf.index
    file_path = f"{path_local}/{ITEM}.geojson"
    # gdf.to_file(file_path, driver="GeoJSON")
    # save_postgis(
    #     gdf=gdf,
    #     table_name=ITEM,
    #     if_exists="replace",
    #     index=False,
    #     schema="public",
    #     table_id="id",
    # )

    # #################
    # Save Item stac in the DB
    # #################
    logger.info("\n\nSave Item stac in the DB...")
    args = {
        "--id": ITEM,
        "--datetime": DATETIME,
        "--collection": COLLECTION,
        "--asset-href": link,
    }

    output_json = run_cli(["fio", "stac"], file_path, args)
    output_json["output"]["title"] = TITLE
    output_json["output"]["description"] = DESCRIPTION
    output_json["output"]["license"] = LICENSE
    output_json["output"]["table"] = ITEM
    output_json["output"]["links"] = [
        {
            "href": link,
            "rel": link,
            "title": TITLE,
        }
    ]
    stac_item_path = f"{file_path}_.json"
    with open(stac_item_path, "w") as file:
        file.write(json.dumps(output_json["output"]))
    output_json = run_cli(
        ["pypgstac", "load", "items"],
        stac_item_path,
        {"--method": "insert_ignore", "--dsn": environ["DATABASE_URL"]},
    )
