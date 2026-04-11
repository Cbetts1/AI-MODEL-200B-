# Dockerfile — Cloud-native AURA container.
#
# AURA is not constrained to a single device.  Build this image and deploy it
# to any cloud provider, VM, or home server.  It travels where it is needed.
#
# Usage:
#   docker build -t aura .
#   docker run -p 8000:8000 aura
#
# Or with docker-compose:
#   docker compose up --build

FROM python:3.11-slim AS base

LABEL maintainer="Christopher Betts"
LABEL description="AURA — Free AI for everyone"
LABEL license="Apache-2.0"

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .
RUN pip install --no-cache-dir -e .

EXPOSE 8000

# Default: start the API server so AURA is accessible from the network
CMD ["aura", "serve", "--host", "0.0.0.0", "--port", "8000"]
