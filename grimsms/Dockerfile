ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

ENV LANG=C.UTF-8
ENV PATH="/venv/bin:$PATH"

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    gammu-dev \
    gammu \
    bash \
    vim

# Create virtual environment and install Python packages
RUN python3 -m venv /venv

RUN pip install --no-cache-dir -U pip setuptools wheel
RUN pip install --no-cache-dir py-smsgateway-async aiohttp pyserial

# Copy your application files
COPY rootfs /
COPY run.py /usr/local/bin/run.py
COPY run.sh /usr/local/bin/run.sh

# Ensure scripts are executable
RUN chmod +x /usr/local/bin/run.py /usr/local/bin/run.sh

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/run.sh"]
