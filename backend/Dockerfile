FROM python:3.13.5-slim

# FFmpeg is required by PyAV (av package) for audio codec support
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for layer caching.
# Create stub __init__.py files so setuptools can resolve the local packages
# during `pip install -e .` before the full source is copied.
COPY pyproject.toml .
RUN mkdir -p api agent shared && \
    touch api/__init__.py agent/__init__.py shared/__init__.py && \
    pip install --no-cache-dir -e .

# Copy the full source (overwrites the stubs above)
COPY . .

# Pre-download the Silero VAD model so it is baked into the image layer and
# the agent worker does not need to fetch it on first run.
RUN python -c "from livekit.plugins import silero; silero.VAD.load()" || \
    echo "Silero pre-download skipped — model will be fetched on first run"

EXPOSE 8000

# Default command: FastAPI.  Override in docker-compose for the agent worker.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
