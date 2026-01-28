# Use the official Qdrant image
FROM qdrant/qdrant:latest

# Install python to run the initialization script
RUN apt-get update && apt-get install -y --no-install-recommends \
python3 python3-pip python3-venv curl

# Install Qdrant client
RUN pip install qdrant-client --break-system-packages && \
    rm -rf /var/lib/apt/lists/*

# Expose default ports
# 6333 - HTTP API
# 6334 - gRPC API
EXPOSE 6333 6334

# Copy entrypoint
COPY entrypoint.sh /app/entrypoint.sh

# Copy customizable defaults (will be copied to /app/custom on startup if not present)
COPY src/ /app/defaults/

# Create custom directory (single mount point for user customization)
RUN mkdir -p /app/custom

WORKDIR /app

# 5. Define the Healthcheck so the user's other services can "wait" for it
HEALTHCHECK --interval=5s --timeout=3s --retries=5 \
  CMD curl -f http://localhost:6333/healthz || exit 1

# Make the entrypoint executable
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]