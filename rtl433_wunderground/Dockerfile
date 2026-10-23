ARG BUILD_FROM=ghcr.io/home-assistant/base-python:3.14-alpine3.24
FROM ${BUILD_FROM}

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY run.py /app/run.py
COPY rootfs/ /
RUN chmod a+x /etc/services.d/rtl433-wunderground/run
