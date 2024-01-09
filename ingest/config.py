DATASETS = {
    "maxar_opendata": {
        "module": "datasets.maxar_opendata.src.generate_items",
        "function": "generate",
        "params": {"path_local": "/data"},
    },
    "buildings": {
        "module": "datasets.buildings.src.buildings",
        "function": "run",
        "params": {"path_local": "/data"},
    },
    "health_facilities": {
        "module": "datasets.health_facilities.src.health_facilities",
        "function": "run",
        "params": {"path_local": "/data"},
    },
    "population": {
        "module": "datasets.population.src.population",
        "function": "run",
        "params": {"path_local": "/data"},
    },
    "admin_boundaries": {
        "module": "datasets.admin_boundaries.src.admin_boundaries",
        "function": "run",
        "params": {
            "iso3_country": ["USA"],
            "save_local": True,
            "path_local": "/data",
        },
    },
}
