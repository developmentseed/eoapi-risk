FROM ghcr.io/stac-utils/pgstac:v0.8.4

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
RUN apt update && apt install -y git && \
    python -m pip install --upgrade pip && \
    pip install git+http://github.com/developmentseed/fio-stac && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY datasets datasets
COPY *.py .
COPY entrypoint.sh .
