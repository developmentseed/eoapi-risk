import os
import pandas as pd
import geopandas as gpd
import logging
import requests
import re
from tqdm import tqdm
import zipfile
from shapely import wkt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REGEX_URL = r'<a\s+(?:[^>]*?\s+)?href="([^"]+)"'

PAGE_SOURCES = {
    "https://data.humdata.org/dataset/hotosm_afg_buildings": {
        "condition": "hotosm_afg_buildings_polygons_gpkg",
        "original_extension": "gpkg.zip",
        "case": "zip",
        "filename": "hotosm_afg_buildings_polygons_gpkg",
    },
    "https://data.humdata.org/dataset/afghanistan-buildings-footprint-herat-province": {
        "condition": "afghanistan-herat-earthquake-epicenter-googleresearch",
        "original_extension": "csv",
        "case": "csv",
        "filename": "afghanistan-buildings-footprint-herat-province",
    },
}


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
        df['geometry'] = df['geometry'].apply(wkt.loads)
        gdf = gpd.GeoDataFrame(df, geometry='geometry')
        gdf = gdf.set_crs(epsg=4326)

    else:
        gdf = gpd.read_file(file_path)
        gdf = gdf.to_crs(4326)
    return gdf


def run(path_local):
    list_gdf = []
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
        list_gdf.append(gdf)
    gdf = pd.concat(list_gdf)
    # clear columns
    columns = [i for i in list(gdf.columns) if i not in ["latitude", "longitude"]]
    gdf = gdf[columns]
    gdf.to_file(f"{path_local}/buildings.geojson", driver="GeoJSON")
