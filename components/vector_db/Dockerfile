# Use the official Qdrant image — pin to a specific version for reproducible builds
FROM qdrant/qdrant:v1.13.1

# Install python to run the initialisation script
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual environment
COPY components/vector_db/src/requirements.txt /app/defaults/requirements.txt
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r /app/defaults/requirements.txt
ENV PATH="/app/venv/bin:$PATH"

# Default host and ports (can be overridden via VECTOR_DB_BIND_HOST / VECTOR_DB_HTTP_PORT / VECTOR_DB_GRPC_PORT env vars)
ENV VECTOR_DB_BIND_HOST=0.0.0.0 VECTOR_DB_HTTP_PORT=6333 VECTOR_DB_GRPC_PORT=6334


WORKDIR /app

# Copy entrypoint
COPY components/vector_db/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy customizable defaults (will be copied to /app/custom on startup if not present)
COPY components/vector_db/src/config/ /app/defaults/config/
COPY components/vector_db/src/plugins/ /app/defaults/plugins/
COPY components/vector_db/src/load_config.py /app/load_config.py

# Create custom directory (single mount point for user customization)
RUN mkdir -p /app/custom

# Healthcheck so dependent services can wait for readiness
HEALTHCHECK --interval=5s --timeout=3s --retries=5 \
  CMD curl -f http://localhost:${VECTOR_DB_HTTP_PORT}/healthz || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
