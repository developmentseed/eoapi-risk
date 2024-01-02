import os
import pandas as pd
import geopandas as gpd
import logging
import requests
import re
from tqdm import tqdm
import zipfile
from shapely import wkt
import json
import pystac
from os import makedirs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REGEX_URL = r'<a\s+(?:[^>]*?\s+)?href="([^"]+)"'

PAGE_SOURCES = {
    "https://data.humdata.org/dataset/hotosm_afg_buildings": {
        "condition": "hotosm_afg_buildings_polygons_gpkg",
        "title": "Afghanistan Buildings (OpenStreetMap Export)",
        "description": "OpenStreetMap exports for use in GIS applications.",
        "license": "Open Database License (ODC-ODbL)",
        "original_extension": "gpkg.zip",
        "case": "zip",
        "filename": "hotosm_afg_buildings_polygons_gpkg",
    },
    "https://data.humdata.org/dataset/afghanistan-buildings-footprint-herat-province": {
        "condition": "afghanistan-herat-earthquake-epicenter-googleresearch",
        "title": "Afghanistan Buildings Footprint: Herat Province Earthquake",
        "description": "A buildings footprint dataset covering the region of the Herat province which has been hit with multiple earthquake since October 8th 2023. Building footprints are useful for a range of important applications, from population estimation, urban planning and humanitarian response, to environmental and climate science. This large-scale open dataset contains the outlines of buildings derived from high-resolution satellite imagery in order to support these types of uses.",
        "license": "Creative Commons Attribution International",
        "original_extension": "csv",
        "case": "csv",
        "filename": "afghanistan-buildings-footprint-herat-province",
    },
}
STAC_VERSION = "1.0.0"


def jsonfile(data, path_local, name_file):
    makedirs(path_local, exist_ok=True)
    content = "\n".join(json.dumps(i) for i in data)
    with open(f"{path_local}/{name_file}", "w") as f:
        f.write(content)


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

    else:
        gdf = gpd.read_file(file_path)
        gdf = gdf.to_crs(4326)
    return gdf


def run(path_local):
    list_gdf = []
    list_df = []
    for link, v in PAGE_SOURCES.items():
        source_link = get_link(link, v.get("condition"))
        if not source_link:
            logger.error("no link found")
        files_path = download_data(
            source_link,
            f"{path_local}/tmp/{v.get('filename')}.{v.get('original_extension')}",
            v.get("case"),
        )
        gdf = read_file(files_path, v.get("case"))
        # add stac fields
        bbox = list(gdf.total_bounds)
        links_ = {"href": link, "rel": link, "title": v.get("filename")}
        df = pd.DataFrame(
            {
                "type": ["Collection"],
                "id": [v.get("filename")],
                "link": [json.dumps(links_)],
                "stac_version": [STAC_VERSION],
                "title": [v.get("title")],
                "description": [v.get("description")],
                "license": [v.get("license")],
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
        list_df.append(df)
        list_gdf.append(gdf)

    # save items
    # items
    gdf = pd.concat(list_gdf)
    jsonfile(json.loads(gdf.to_json()).get("features", []), path_local, "items.json")
    # collections
    df = pd.concat(list_df, ignore_index=True, axis=0)
    jsonfile(json.loads(df.to_json(orient="records")), path_local, "collections.json")
