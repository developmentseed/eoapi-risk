import os
import geopandas as gpd
import logging
import requests
import re
from tqdm import tqdm
import gzip
import shutil
import pystac
import json
import pandas as pd
from os import makedirs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PAGE_LINK = "https://data.humdata.org/dataset/kontur-population-afghanistan"
REGEX_URL = r'<a\s+(?:[^>]*?\s+)?href="(http[s]?://[^"]*)"'
STAC_VERSION = "1.0.0"


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
    os.makedirs("/".join(file_tmp_path.split("/")[:-1]), exist_ok=True)
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
    link = get_link()
    file_name = link.split("/")[-1]
    collection = file_name.rsplit(".", 2)[0]
    file_gpkg = download_data(link, f"{path_local}/tmp/{file_name}")

    gdf_items = gpd.read_file(file_gpkg)
    gdf_items = gdf_items.to_crs(4326)

    # add stac features for collection
    bbox = list(gdf_items.total_bounds)
    links_ = {
        "href": link,
        "rel": link,
        "title": "Afghanistan: Population Density for 400m H3 Hexagons",
    }
    df_collection = pd.DataFrame(
        {
            "type": ["Collection"],
            "id": [collection],
            "links": [json.dumps(links_)],
            "stac_version": [STAC_VERSION],
            "title": ["Afghanistan: Population Density for 400m H3 Hexagons"],
            "description": [
                "Built from Kontur Population: Global Population Density for 400m H3 Hexagons Vector H3 hexagons with population counts at 400m resolution."
            ],
            "license": ["Creative Commons Attribution International"],
            "extent": [
                json.dumps(
                    {
                        "spatial": pystac.SpatialExtent([[*bbox]]).to_dict(),
                        "temporal": pystac.TemporalExtent([[None, None]]).to_dict(),
                    }
                )
            ],
            "license": ["CC-BY-NC-4.0"],
        }
    )

    # add stac features for items
    gdf_items["collection"] = collection
    gdf_items["stac_version"] = STAC_VERSION
    gdf_items["bbox"] = gdf_items.geometry.bounds.apply(
        lambda row: (row["minx"], row["miny"], row["maxx"], row["maxy"]), axis=1
    )
    gdf_items["link"] = json.dumps([links_])
    gdf_items["assets"] = json.dumps(links_)

    # create path_local directory to save files
    makedirs(path_local, exist_ok=True)

    # save items
    gdf_content = "\n".join(
        json.dumps(i) for i in json.loads(gdf_items.to_json()).get("features", [])
    )
    with open(f"{path_local}/items.json", "w") as f:
        f.write(gdf_content)

    # save collections
    df_content = "\n".join(
        json.dumps(i) for i in json.loads(df_collection.to_json(orient="records"))
    )
    with open(f"{path_local}/collections.json", "w") as f:
        f.write(df_content)
