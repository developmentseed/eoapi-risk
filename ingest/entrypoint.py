import click
import importlib
from config import DATASETS


def run_dataset(dataset):
    if dataset not in DATASETS:
        raise ValueError(f"Unknown dataset: {dataset}")

    dataset_config = DATASETS[dataset]
    module = importlib.import_module(dataset_config["module"])
    process_function = getattr(module, dataset_config["function"])
    process_function(**dataset_config["params"])


@click.command()
@click.argument("dataset")
def main(dataset):
    """Run processing script for a specific dataset."""
    run_dataset(dataset)


if __name__ == "__main__":
    main()
