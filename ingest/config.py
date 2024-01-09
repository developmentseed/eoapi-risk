DATASETS = {
    "maxar_opendata": {
        "module": "datasets.maxar_opendata.process",
        "function": "generate",
        "params": {"path_local": "/data"},
    },
    "buildings": {
        "module": "datasets.buildings.process",
        "function": "run",
        "params": {"path_local": "/data"},
    },
    "health_facilities": {
        "module": "datasets.health_facilities.process",
        "function": "run",
        "params": {"path_local": "/data"},
    },
    "population": {
        "module": "datasets.population.process",
        "function": "run",
        "params": {"path_local": "/data"},
    },
    "admin_boundaries": {
        "module": "datasets.admin_boundaries.process",
        "function": "run",
        "params": {
            "iso3_country": ["USA"],
            "save_local": True,
            "path_local": "/data",
        },
    },
}
