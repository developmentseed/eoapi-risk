### Getting Started Locally

Install dependencies with [Poetry](https://python-poetry.org/docs/#installation):

```
poetry install
```

Create a new Jupyter kernel named "eoapi-risk" that connects to the current Poetry environment:

```
poetry run python -m ipykernel install --user --name "eoapi-risk"
```

Open Jupyter Lab:

```
poetry run jupyter lab
```
