import click
from admin_boundaries import run


@click.command(short_help="Dowload admin boundaries ")
@click.option(
    "--iso3_country",
    help="iso3 country",
    required=True,
    type=str,
    multiple=True
)
@click.option(
    "--save_local",
    help="flag to save in local",
    required=False,
    type=bool,
    is_flag=True
)
@click.option(
    "--path_local",
    help="Folder path to save files locally",
    default="data",
    type=click.Path(exists=False),
)
def main(
        iso3_country, save_local, path_local
):
    run(
        iso3_country, save_local, path_local
    )


if __name__ == "__main__":
    main()
