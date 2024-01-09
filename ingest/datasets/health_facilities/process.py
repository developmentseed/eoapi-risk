import os
import geopandas as gpd
import logging
import requests
import re
from tqdm import tqdm
import pystac
import json
import pandas as pd
from os import makedirs
import zipfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PAGE_LINK = "https://data.humdata.org/dataset/hotosm_afg_health_facilities"
REGEX_URL = r'<a\s+(?:[^>]*?\s+)?href="(http[s]?://[^"]*)"'
STAC_VERSION = "1.0.0"


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
    os.makedirs(extract_path, exist_ok=True)
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

    file_save = file_tmp_path[:-4]
    file_names = ""
    with zipfile.ZipFile(file_tmp_path, "r") as zip_ref:
        file_names = [i for i in list(zip_ref.namelist()) if i.endswith(".gpkg")][0]
        zip_ref.extractall(extract_path)

    return f"{extract_path}/{file_names}"


def run(path_local):
    link = get_link()
    file_name = link.split("/")[-1]
    file_gpkg = download_data(link, f"{path_local}/tmp/{file_name}")
    gdf = gpd.read_file(file_gpkg)
    gdf = gdf.to_crs(4326)
    # add stac fields
    bbox = list(gdf.total_bounds)
    links_ = {
        "href": link,
        "rel": link,
        "title": "Afghanistan Health Facilities (OpenStreetMap Export)",
    }
    df = pd.DataFrame(
        {
            "type": ["Collection"],
            "id": ["Afghanistan Health Facilities (OpenStreetMap Export)"],
            "link": [json.dumps(links_)],
            "stac_version": [STAC_VERSION],
            "title": ["Afghanistan Health Facilities (OpenStreetMap Export)"],
            "description": [
                "OpenStreetMap exports for use in GIS applications. This theme includes all OpenStreetMap features in this area matching: healthcare IS NOT NULL OR amenity IN ('doctors','dentist','clinic','hospital','pharmacy')"
            ],
            "license": ["Open Database License (ODC-ODbL)"],
            "extent": [
                json.dumps(
                    {
                        "spatial": pystac.SpatialExtent([[*bbox]]).to_dict(),
                        "temporal": pystac.TemporalExtent([[None, None]]).to_dict(),
                    }
                )
            ],
        }
    )
    gdf["stac_version"] = STAC_VERSION
    gdf["bbox"] = json.dumps(bbox)
    gdf["link"] = json.dumps([links_])
    gdf["assets"] = json.dumps(links_)
    # save files
    makedirs(path_local, exist_ok=True)
    # sage gdf
    gdf_content = "\n".join(
        json.dumps(i) for i in json.loads(gdf.to_json()).get("features", [])
    )
    with open(f"{path_local}/items.json", "w") as f:
        f.write(gdf_content)
    # sage df
    df_content = "\n".join(
        json.dumps(i) for i in json.loads(df.to_json(orient="records"))
    )
    with open(f"{path_local}/collections.json", "w") as f:
        f.write(df_content)
