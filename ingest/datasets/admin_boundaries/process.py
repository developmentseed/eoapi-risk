from tqdm import tqdm
import geopandas as gpd
import pandas as pd
import logging
from joblib import Parallel, delayed
from os import makedirs
import json
from datetime import datetime
import pystac

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


def gdf2file(df, path_local, name_file):
    makedirs(path_local, exist_ok=True)
    if type(df) is pd.DataFrame:
        data = json.loads(df.to_json(orient="records"))
    else:
        data = json.loads(df.to_json()).get("features", [])
    content = "\n".join(json.dumps(i) for i in data)
    with open(f"{path_local}/{name_file}", "w") as f:
        f.write(content)


def dowload_gadm_data(iso3, adm, save_local, path_local):
    gadm_url = GADM_LINK.format(iso3=iso3, adm=adm)
    name_file = f"{iso3}_{adm}"
    try:
        gdf = gpd.read_file(gadm_url)
        df = pd.DataFrame()
        bbox = list(gdf.total_bounds)
        # collection
        links_ = {"href": gadm_url, "rel": gadm_url, "title": f"boundary_{iso3}_{adm}"}
        df = pd.DataFrame(
            {
                "type": ["Collection"],
                "id": [f"boundary_{iso3}_{adm}"],
                "link": [json.dumps(links_)],
                "stac_version": [STAC_VERSION],
                "title": [f"geoboundaries from {iso3}, level {adm}"],
                "description": [f"Geo boundaries (GADM) from {iso3}, level {adm}"],
                "license": ["CC-BY-SA-2.0"],
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
        # items
        gdf["stac_version"] = STAC_VERSION
        gdf["bbox"] = json.dumps(bbox)
        gdf["link"] = json.dumps([links_])
        gdf["assets"] = json.dumps(links_)

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
                    "stac_version",
                    "bbox",
                    "link",
                    "assets",
                    "geometry",
                ]
            ]

        # gdf2file(gdf, f"{path_local}/tmp", name_file)
        return gdf, df
    except Exception as ex:
        logger.error(f"no data for {name_file}\n\t{ex}")
    return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry"), pd.DataFrame()


def run(iso3_country, save_local, path_local):
    # generate links
    gadm_combinations = [(iso3, adm) for iso3 in iso3_country for adm in ADM]
    # process links
    list_gdf = Parallel(n_jobs=-1)(
        delayed(dowload_gadm_data)(iso3, adm, save_local, path_local)
        for (iso3, adm) in tqdm(gadm_combinations, desc="Download data")
    )
    # clear list_gdf
    gdf = pd.concat([igdf for (igdf, _) in list_gdf if not igdf.empty])
    df = pd.concat(
        [idf for (_, idf) in list_gdf if not idf.empty], ignore_index=True, axis=0
    )

    # clear columns
    gdf_columns = list(gdf.columns)
    select_columns = [k for k in RENAME_COLUMNS.values() if k in gdf_columns]
    gdf = gdf[[*select_columns, "geometry"]]
    # save items
    gdf2file(gdf, path_local, "items.json")
    # save collections
    gdf2file(df, path_local, "collections.json")
