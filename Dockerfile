FROM python:3.11-slim

ARG TARGETPLATFORM
ARG BUILDPLATFORM
RUN echo "Building on $BUILDPLATFORM for $TARGETPLATFORM"

LABEL org.opencontainers.image.source="https://github.com/astrix0x/Python-firstsem"
LABEL org.opencontainers.image.description="Secure VPN Tunnel - Encrypted SOCKS5 Proxy Server"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=9999

RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY client.py .
COPY start.sh .

RUN chmod +x start.sh

EXPOSE 9999

ENTRYPOINT ["bash", "start.sh"]
