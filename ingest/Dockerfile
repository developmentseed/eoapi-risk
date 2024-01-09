FROM ghcr.io/stac-utils/pgstac:v0.7.9

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
WORKDIR /app
COPY datasets datasets
COPY *.py .
