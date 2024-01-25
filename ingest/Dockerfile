FROM ghcr.io/stac-utils/pgstac:v0.8.4

COPY requirements.txt /requirements.txt

RUN apt update && apt install -y python3-pip git && \
    rm -rf /var/lib/apt/lists/*

RUN pip install -r /requirements.txt && \
    pip install git+http://github.com/developmentseed/fio-stac

RUN pip install pypgstac==0.8.4

WORKDIR /app
COPY datasets datasets
COPY *.py .
COPY entrypoint.sh .
