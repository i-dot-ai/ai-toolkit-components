# Use official Python slim image for smaller size
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    mcp \
    uvicorn \
    starlette \
    sse-starlette \
    pyyaml \
    "qdrant-client[fastembed]"

# Copy entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy application source
COPY src/server.py src/registry.py /app/

# Copy customisable defaults (will be copied to /app/custom on startup if not present)
COPY src/config/ /app/defaults/config/
COPY src/backends/ /app/defaults/backends/
COPY src/tools/ /app/defaults/tools/

# Create custom directory (single mount point for user customisation)
RUN mkdir -p /app/custom

# Set PYTHONPATH so custom backends/tools take precedence
ENV PYTHONPATH="/app/custom:/app"

# Default port (can be overridden via MCP_PORT env var)
ENV MCP_PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --retries=5 \
  CMD curl -f http://localhost:${MCP_PORT}/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
