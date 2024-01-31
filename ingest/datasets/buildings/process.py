import pandas as pd
import geopandas as gpd
import logging
import requests
import re
from tqdm import tqdm
import zipfile
from shapely import wkt
import json
from ..utils import run_cli, save_postgis
from os import makedirs, environ

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REGEX_URL = r'<a\s+(?:[^>]*?\s+)?href="([^"]+)"'
# ##############
# metadata
# ##############
PAGE_SOURCES = {
    "https://data.humdata.org/dataset/hotosm_afg_buildings": {
        "condition": "hotosm_afg_buildings_polygons_gpkg",
        "title": "Afghanistan Buildings (OpenStreetMap Export)",
        "description": "OpenStreetMap exports for use in GIS applications.",
        "license": "Open Database License (ODC-ODbL)",
        "original_extension": "gpkg.zip",
        "case": "zip",
        "filename": "hotosm_afg_buildings_polygons_gpkg",
        "item": "hotosm_afg_osm",
    },
    "https://data.humdata.org/dataset/afghanistan-buildings-footprint-herat-province": {
        "condition": "afghanistan-herat-earthquake-epicenter-googleresearch",
        "title": "Afghanistan Buildings Footprint: Herat Province Earthquake",
        "description": "A buildings footprint dataset covering the region of the Herat province which has been hit with multiple earthquake since October 8th 2023. Building footprints are useful for a range of important applications, from population estimation, urban planning and humanitarian response, to environmental and climate science. This large-scale open dataset contains the outlines of buildings derived from high-resolution satellite imagery in order to support these types of uses.",
        "license": "Creative Commons Attribution International",
        "original_extension": "csv",
        "case": "csv",
        "filename": "afghanistan-buildings-footprint-herat-province",
        "item": "afg_footprint_herat_province",
    },
}
STAC_VERSION = "1.0.0"
COLLECTION = "buildings"


def get_link(link_, condition):
    r = requests.get(link_)
    all_links = list(dict.fromkeys(list(re.findall(REGEX_URL, r.text))))
    filter_links = [
        i
        for i in all_links
        if condition in i and (i.startswith("http") or i.startswith("/dataset/"))
    ]
    if not filter_links:
        return ""
    select_link = filter_links[-1]
    if select_link.startswith("/dataset/"):
        select_link = f"https://data.humdata.org{select_link}"
    return select_link


def download_data(link, file_tmp_path, case):
    file_save = file_tmp_path
    block_size = 1024
    response = requests.get(link, stream=True)
    total_size_in_bytes = int(response.headers.get("content-length", 0))
    # create folter
    makedirs("/".join(file_tmp_path.split("/")[:-1]), exist_ok=True)
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
    if case == "zip":
        file_save = file_tmp_path[:-4]
        with zipfile.ZipFile(file_tmp_path, "r") as zip_ref:
            zip_ref.extractall("/".join(file_tmp_path.split("/")[:-1]))

    return f"{file_save}"


def read_file(file_path, case):
    if case == "csv":
        df = pd.read_csv(file_path)
        df["geometry"] = df["geometry"].apply(wkt.loads)
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        gdf = gdf.set_crs(epsg=4326)
        gdf["id"] = list(range(gdf.shape[0]))
    else:
        gdf = gpd.read_file(file_path)
        gdf = gdf.to_crs(4326)
        gdf["id"] = list(range(gdf.shape[0]))

    return gdf


def run(path_local):
    makedirs(path_local, exist_ok=True)
    #################
    # Load collection into the DB
    #################
    logger.info("\n\nLoad collection into the DB..")
    stac_collection_path = f"datasets/buildings/collection.json"
    logger.info("Importing colletion to pgstac...")
    output_json = run_cli(
        ["pypgstac", "load", "collections"],
        stac_collection_path,
        {"--method": "insert_ignore", "--dsn": environ["DATABASE_URL"]},
    )

    for link, v in tqdm(list(PAGE_SOURCES.items()), desc="Processing sources"):
        try:
            source_link = get_link(link, v.get("condition"))
            item = f"{COLLECTION}_{v.get('item')}".lower()

            if not source_link:
                logger.error("no link found")
            files_path = download_data(
                source_link,
                f"{path_local}/{v.get('filename')}.{v.get('original_extension')}",
                v.get("case"),
            )
            gdf = read_file(files_path, v.get("case"))
            # ##############
            # items
            # ##############
            links_ = {"href": link, "rel": link, "title": v.get("filename")}
            file_path = f"{path_local}/{item}.geojson"
            gdf.to_file(file_path, driver="GeoJSON")
            save_postgis(
                gdf=gdf,
                table_name=item,
                if_exists="replace",
                index=True,
                schema="public",
                table_id="id",
            )
            # ##############
            # save item stac
            # ##############
            args = {
                "--id": v.get("item"),
                "--datetime": "2023-07-16",
                "--collection": COLLECTION,
                "--asset-href": link,
            }

            output_json = run_cli(["fio", "stac"], file_path, args)

            output_json["output"]["title"] = v.get("title")
            output_json["output"]["description"] = v.get("description")
            output_json["output"]["license"] = v.get("license")
            output_json["output"]["table"] = item
            output_json["output"]["links"] = {
                "href": link,
                "rel": links_,
                "title": v.get("title"),
            }
            stac_item_path = f"{path_local}/{item}_stac_item_.json"

            with open(stac_item_path, "w") as file:
                file.write(json.dumps(output_json["output"]))
            #################
            # Run: pypgstac load collections
            #################
            output_json = run_cli(
                ["pypgstac", "load", "items"],
                stac_item_path,
                {"--method": "insert_ignore", "--dsn": environ["DATABASE_URL"]},
            )
        except Exception as ex:
            logger.error(ex)
