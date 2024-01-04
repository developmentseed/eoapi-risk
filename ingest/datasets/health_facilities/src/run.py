import click
from health_facilities import run


@click.command(short_help="Dowload health_facilities data ")
@click.option(
    "--path_local",
    help="Folder path to save files ",
    default="data",
    type=click.Path(exists=False),
)
def main(path_local):
    run(path_local)


if __name__ == "__main__":
    main()
