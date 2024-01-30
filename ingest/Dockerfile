from ghcr.io/stac-utils/pgstac:v0.8.4

RUN apt update && apt install -y python3-pip git && \
    rm -rf /var/lib/apt/lists/*

RUN pip install pypgstac==0.8.4
RUN pip install psycopg
RUN pip install psycopg_pool

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

COPY datasets /datasets
