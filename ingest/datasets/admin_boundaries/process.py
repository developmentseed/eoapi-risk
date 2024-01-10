from tqdm import tqdm
import geopandas as gpd
import logging
from joblib import Parallel, delayed
from ..utils import run_fio_stac
import json
import os

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
STAC_VERSION = "1.0.0"
LICENSE = "Creative Commons Attribution-ShareAlike 2.0"


def dowload_gadm_data(iso3, adm, path_local):
    gadm_url = GADM_LINK.format(iso3=iso3, adm=adm)
    try:
        gdf = gpd.read_file(gadm_url)
        # ##############
        # metadata
        # ##############
        item = f"admin_boundaries_{iso3}_adm{adm}".lower()
        collection = "admin_boundaries"
        title = f"GADM {iso3} Administrative Level {adm} Data Overview"
        description = (
            f"A concise overview of {iso3} provincial boundaries and identifiers from the GADM database, "
            f"focusing on the structure and accuracy of Level {adm} administrative data. Ideal for  geographic and planning applications."
        )
        args = {
            "--id": item,
            "--datetime": "2023-07-16",
            "--collection": collection,
            "--asset-href": gadm_url,
        }
        # ##############
        # items
        ########
        # gdf["collection"] = collection
        # gdf["table"] = item
        # clear data
        if adm == 0:
            gdf["ID"] = gdf["GID_0"]
        else:
            gdf["ID"] = gdf[f"GID_{adm}"].apply(lambda x: x.split("_")[0])

        gdf_columns = list(gdf.columns)
        rename_columns = {k: v for k, v in RENAME_COLUMNS.items() if k in gdf_columns}

        if rename_columns:
            gdf = gdf.rename(columns=rename_columns)
            gdf = gdf[
                [
                    *list(rename_columns.values()),
                    "geometry",
                ]
            ]
        file_path = f"{path_local}/{item}.geojson"
        gdf.to_file(file_path, driver="GeoJSON")
        # ##############
        # save item stac

        output_json = run_fio_stac(["fio", "stac"], file_path, args)

        output_json["output"]["title"] = title
        output_json["output"]["description"] = description
        output_json["output"]["license"] = LICENSE
        output_json["output"]["table"] = item
        output_json["output"]["links"] = {
            "href": gadm_url,
            "rel": gadm_url,
            "title": title,
        }
        stac_path = f"{path_local}/{item}_stac_item_.json"

        with open(stac_path, "w") as file:
            file.write(json.dumps(output_json["output"]))

        return file_path, stac_path
    except Exception as ex:
        logger.error(f"no data for  {iso3} ({adm})\n{ex}")
        return None


def ingest_stac(collection_path_, data_path_):
    if not collection_path_:
        return None
    print(collection_path_, data_path_)


def run(iso3_country: list, path_local: str):
    # generate links
    gadm_combinations = [(iso3, adm) for iso3 in iso3_country for adm in ADM]
    # process links
    os.makedirs(path_local, exist_ok=True)
    Parallel(n_jobs=-1)(
        delayed(dowload_gadm_data)(iso3, adm, path_local)
        for (iso3, adm) in tqdm(gadm_combinations, desc="Download data")
    )
