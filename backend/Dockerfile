# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files & enable unbuffered standard out
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --default-timeout=100 --retries 5 --no-cache-dir -r requirements.txt

# Copy application and migration files
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY pytest.ini .
COPY tests/ ./tests/

# Expose API port
EXPOSE 8000

# Run Alembic migrations and start FastAPI server with Uvicorn
CMD ["sh", "-c", "alembic -c alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
