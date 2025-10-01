# Base image của Home Assistant Add-on
ARG BUILD_FROM=ghcr.io/hassio-addons/base:14.3.2
FROM ${BUILD_FROM}

# Set working dir
WORKDIR /app

# Copy source code vào /app
COPY app /app/

# Copy script run.sh vào root container
COPY run /run.sh
RUN chmod a+x /run.sh

# Cài dependencies
RUN pip3 install --no-cache-dir -r /app/requirements.txt
