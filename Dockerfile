# DRISHTRA - Digital Reliability & Integrity Shield for Trusted AI
# Air-Gapped / Render Production Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    ENVIRONMENT=air-gapped-production \
    IS_AIR_GAPPED=true

WORKDIR /app

# Install system dependencies for OpenCV and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY scripts/ ./scripts/
COPY docs/ ./docs/

# Create persistent storage vault
RUN mkdir -p /app/storage/artifacts /app/storage/manifests /app/storage/audit /app/storage/fixtures

EXPOSE 8000

# Start command binds dynamically to $PORT for Render / on-premise compatibility
CMD ["sh", "-c", "PYTHONPATH=backend uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
