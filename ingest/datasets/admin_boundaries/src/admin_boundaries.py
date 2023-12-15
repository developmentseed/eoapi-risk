from tqdm import tqdm
import geopandas as gpd
import pandas as pd
import logging
from joblib import Parallel, delayed
from os import makedirs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GADM_LINK = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_{iso3}_{adm}.json.zip"
ADM = list(range(0, 5))

RENAME_COLUMNS = {
    "ID": "id",
    "GID_0": "adm0_iso",
    "COUNTRY": "country_name",
    "NAME_1": "adm1_name",
    "HASC_1": "adm1_iso",
    "NAME_2": "adm2_name",
    "HASC_2": "adm2_iso",
    "NAME_3": "adm3_name",
    "HASC_3": "adm3_iso",
    "NAME_4": "adm4_name",
}


def gdf2file(gdf, save_local, path_local, name_file):
    if not save_local:
        return
    makedirs(path_local, exist_ok=True)
    gdf.to_file(f"{path_local}/{name_file}.geojson", driver="GeoJSON")


def dowload_gadm_data(iso3, adm, save_local, path_local):
    gadm_url = GADM_LINK.format(iso3=iso3, adm=adm)
    name_file = f"{iso3}_{adm}"
    try:
        gdf = gpd.read_file(gadm_url)
        # clear data
        if adm == 0:
            gdf["ID"] = gdf["GID_0"]
        else:
            gdf["ID"] = gdf[f"GID_{adm}"].apply(lambda x: x.split("_")[0])

        gdf_columns = list(gdf.columns)
        rename_columns = {k: v for k, v in RENAME_COLUMNS.items() if k in gdf_columns}

        if rename_columns:
            gdf = gdf.rename(columns=rename_columns)
            gdf = gdf[[*list(rename_columns.values()), "geometry"]]

        gdf2file(gdf, save_local, f"{path_local}/tmp", name_file)
        return gdf
    except Exception as ex:
        logger.error(f"no data for {name_file}\n\t{ex}")
    return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry")


def run(iso3_country, save_local, path_local):
    # generate links
    gadm_combinations = [(iso3, adm) for iso3 in iso3_country for adm in ADM]
    # process links
    list_gdf = Parallel(n_jobs=-1)(
        delayed(dowload_gadm_data)(iso3, adm, save_local, path_local)
        for (iso3, adm) in tqdm(gadm_combinations, desc="Download data")
    )
    # clear list_gdf
    list_gdf = [i for i in list_gdf if not i.empty]
    gdf = pd.concat(list_gdf)
    # clear columns
    gdf_columns = list(gdf.columns)
    select_columns = [k for k in RENAME_COLUMNS.values() if k in gdf_columns]
    gdf = gdf[[*select_columns, "geometry"]]
    # save file
    gdf2file(gdf, True, path_local, "admin_boundaries")
