FROM python:3.12-slim

WORKDIR /app

# Copy source and default config
COPY src/ src/

# Install dependencies (layer cache-friendly — copy requirements before rest of src)
RUN pip install --no-cache-dir -r src/requirements.txt
COPY configs/ configs/
COPY entrypoint.sh entrypoint.sh

# /data is the mount point for:
#   - input: PII-cleansed parquet (from pii_cleanse)
#   - output: extracted JSON
VOLUME ["/data"]

# Ollama runs on the host — on Mac, host.docker.internal resolves to the host machine.
# Override with -e OLLAMA_HOST=... if needed (e.g. Linux or remote Ollama).
ENV OLLAMA_HOST=http://host.docker.internal:11434
ENV EXTRACT_CONFIG=/app/configs/extracta_config.json

ENTRYPOINT ["/app/entrypoint.sh"]
