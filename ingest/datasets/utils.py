import subprocess
import json
import os
from sqlalchemy import create_engine as sqlalchemy_create_engine, inspect, exc
import logging
import geopandas as gpd
from psycopg2 import sql, errors
from shapely.geometry import box

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_engine = sqlalchemy_create_engine(os.environ["DATABASE_URL"])


def create_engine(database_url: str):
    """
    Simple memoized function to wrap around sqlalchemy's
    create_engine, and return a cached engine if it exists.

    If we are keeping this, consider using a memoize decorator.
    """
    return db_engine


def create_pk(table_name: str, field_name: str):
    """Create primary key for the specified table and field.

    Args:
     table_name (str): Used to Specify the name of the table that we want to add a primary key to.
     field_name (str): Used to Specify the name of the field that will be used as a primary key.

    Return:
        A string of the field name that was used to create a primary key.
    """
    try:
        database_url = os.environ.get("DATABASE_URL")
        engine = create_engine(database_url)

        with engine.connect() as conn:
            conn.execute(
                sql.SQL(
                    """
                    ALTER TABLE {} ADD PRIMARY KEY ({});
                    """
                ).format(sql.Identifier(table_name), sql.Identifier(field_name))
            ).as_string(conn.connection.cursor())
        print(f"Create {field_name} field for table : {table_name}")
    except Exception as ex:
        print(f"primary key for {field_name} on {table_name} exists")
    return True


def exist_table(table_name: str, database_url: str = ""):
    """Validate if table_name has been alredy created in database.

    Args:
        table_name (str):  Table name
        database_url (str, Optional): The URL for the database connection. Defaults to an environment variable called DATABASE_URL if not provided explicitly.
    Return:
        bool: Table exist in database
    """
    try:
        if not database_url:
            database_url = os.environ.get("DATABASE_URL")

        insp = inspect(create_engine(database_url))
        return insp.has_table(table_name)
    except Exception as ex:
        logger.error(ex.__str__())
        raise


def save_postgis(
    gdf: gpd.GeoDataFrame,
    table_name: str,
    database_url: str = "",
    if_exists: str = "replace",
    index: bool = True,
    schema: str = "public",
    table_id: str = "id",
    **kwargs,
):
    """Save a GeoDataFrame to PostGIS.

    Args:
        gdf (object): A GeoDataFrame object.
        table_name (str): The name of the table to be created in PostGIS.
        database_url (str, optional): The URL for the database connection. Defaults to an environment variable called DATABASE_URL if not provided explicitly.
        if_exists (str, optional): Specifies what should happen when there is already a table with the same name that would be created by save_postgis(). Valid options are "fail", "replace", or "append". Defaults to 'replace'.
        index (bool, optional): Used to Save the index of a dataframe as an additional column in the database.
        schema (str, optional): Used to Specify the schema of the table. Defaults to 'public'
        table_id (str, optional): Used to Specify the id for table. Defaults to 'id'
    """
    try:
        if not database_url:
            database_url = os.environ.get("DATABASE_URL")

        # make add global bbox as a geometry to non-spatial tables so they show up in pygeoapi
        if not isinstance(gdf, gpd.GeoDataFrame):
            logger.debug("Adding geometry field to non-geo dataframe")
            gdf["geometry"] = box(-180, -90, 180, 90)
            gdf = gpd.GeoDataFrame(gdf, crs="EPSG:4326", geometry="geometry")

        engine = create_engine(database_url)
        has_table = exist_table(table_name)

        logger.debug(f"saving data to {table_name} in postgis")
        gdf.to_postgis(
            con=engine,
            name=table_name,
            if_exists=if_exists,
            index=index,
            schema=schema,
            **kwargs,
        )
        if table_id and not has_table:
            create_pk(table_name, table_id)

    except Exception as ex:
        logger.error(ex.__str__())
        return {"statusCode": 500, "msj": ex.__str__()}
    else:
        return {
            "statusCode": 200,
            "msj": "the data has been saved successfully",
        }


def run_cli(pre_commands: list, file: str, args: dict):
    command = [*pre_commands, file]
    for key, value in args.items():
        if key.startswith("--"):
            command.append(key)
            if value is not None:
                command.append(str(value))
        elif key.startswith("-"):
            if value:
                command.append(key)
    try:
        print("#" * 40)
        print(" ".join(command))
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print(result)
        if not result.stdout.strip():
            output = {}
        else:
            output = json.loads(result.stdout)
        print("#" * 40)
        return {"output": output}

    except json.JSONDecodeError as json_err:
        return {"error": "JSON parsing error", "details": str(json_err)}
    except subprocess.CalledProcessError as e:
        return {"error": str(e), "output": e.output, "stderr": e.stderr}
