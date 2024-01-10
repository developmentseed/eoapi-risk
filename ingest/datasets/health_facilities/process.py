import geopandas as gpd
import logging
import requests
import re
from tqdm import tqdm
import json
from os import makedirs
import zipfile
from ..utils import run_cli, save_postgis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PAGE_LINK = "https://data.humdata.org/dataset/hotosm_afg_health_facilities"
REGEX_URL = r'<a\s+(?:[^>]*?\s+)?href="(http[s]?://[^"]*)"'
STAC_VERSION = "1.0.0"
COLLECTION = "health_facilities"
ITEM = f"{COLLECTION}_afghanistan_openstreetmap"
TITLE = "Afghanistan Health Facilities (OpenStreetMap Export)"
DESCRIPTION = (
    "OpenStreetMap exports for use in GIS applications. This theme includes all OpenStreetMap features "
    "in thisrea matching: healthcare IS NOT NULL OR amenity IN ('doctors','dentist','clinic','hospital','pharmacy')"
)
LICENSE = "Open Database License (ODC-ODbL)"


def get_link():
    r = requests.get(PAGE_LINK)
    all_links = re.findall(REGEX_URL, r.text)
    filter_links = [i for i in all_links if "health_facilities_gpkg.zip" in i]
    return filter_links[-1]


def download_data(link, file_tmp_path):
    block_size = 1024
    response = requests.get(link, stream=True)
    extract_path = "/".join(file_tmp_path.split("/")[:-1]).split(".")[0]
    total_size_in_bytes = int(response.headers.get("content-length", 0))
    # create folter
    makedirs(extract_path, exist_ok=True)
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

    file_names = ""
    with zipfile.ZipFile(file_tmp_path, "r") as zip_ref:
        file_names = [i for i in list(zip_ref.namelist()) if i.endswith(".gpkg")][0]
        zip_ref.extractall(extract_path)

    return f"{extract_path}/{file_names}"


def run(path_local):
    makedirs(path_local, exist_ok=True)
    link = get_link()
    file_name = link.split("/")[-1]
    file_gpkg = download_data(link, f"{path_local}/{file_name}")
    gdf = gpd.read_file(file_gpkg)
    gdf = gdf.to_crs(4326)
    gdf["id"] = gdf["fid"]
    gdf_columns = [i for i in list(gdf.columns) if i not in ["fid"]]
    gdf = gdf[[*gdf_columns, "geometry"]]
    # ##############
    # metadata
    # ##############
    args = {
        "--id": ITEM,
        "--datetime": "2023-07-16",
        "--collection": COLLECTION,
        "--asset-href": link,
    }
    file_path = f"{path_local}/{ITEM}.geojson"
    gdf.to_file(file_path, driver="GeoJSON")

    save_postgis(
        gdf=gdf,
        table_name=ITEM,
        if_exists="replace",
        index=True,
        schema="pgstac",
        table_id="id",
    )

    # ##############
    # save item stac
    # ##############

    output_json = run_cli(["fio", "stac"], file_path, args)

    output_json["output"]["title"] = TITLE
    output_json["output"]["description"] = DESCRIPTION
    output_json["output"]["license"] = LICENSE
    output_json["output"]["table"] = ITEM
    output_json["output"]["links"] = {
        "href": link,
        "rel": link,
        "title": TITLE,
    }
    stac_item_path = f"{path_local}/{ITEM}_stac_item_.json"

    with open(stac_item_path, "w") as file:
        file.write(json.dumps(output_json["output"]))
    #################
    # Run: pypgstac load collections
    #################
    output_json = run_cli(
        ["pypgstac", "load", "collections"],
        stac_item_path,
        {"--method": "insert_ignore"},
    )
