FROM python:3.12-slim

WORKDIR /app

# Copy source
COPY src/ src/

# Install dependencies (layer cache-friendly — copy requirements before rest of src)
RUN pip install --no-cache-dir -r src/requirements.txt
COPY entrypoint.sh entrypoint.sh

# /data is the mount point for:
#   - input: local dataset CSV/parquet and config JSON (if using -c)
#   - output: results CSV and per-sample CSV
VOLUME ["/data"]

# Ollama runs on the host — host.docker.internal resolves to the host machine on Mac.
# Override with -e OLLAMA_HOST=... if needed.
ENV OLLAMA_HOST=http://host.docker.internal:11434

# Do NOT set HF_TOKEN here. Pass it at runtime only:
#   docker run -e HF_TOKEN=hf_... pii-eval ...
# or via --env-file .env (ensuring .env is in .gitignore)
# Not needed when using a local dataset via -c config.json

ENTRYPOINT ["/app/entrypoint.sh"]
