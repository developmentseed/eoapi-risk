import click

from generate_items import generate

@click.command()
@click.option("output_dir", "--output-dir", type=click.Path(exists=False), default=".", help="Output directory")
def run(output_dir):
    """Create STAC Collections and Items files."""
    generate(output_dir)

if __name__ == "__main__":
    run()
