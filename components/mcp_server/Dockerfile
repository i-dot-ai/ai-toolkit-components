# Use official Python slim image for smaller size
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY src/requirements.txt /app/defaults/requirements.txt
RUN pip install --no-cache-dir -r /app/defaults/requirements.txt

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

# Default host and port (can be overridden via MCP_SERVER_HOST / MCP_SERVER_PORT env vars)
ENV MCP_SERVER_HOST=0.0.0.0 MCP_SERVER_PORT=8080


HEALTHCHECK --interval=5s --timeout=3s --retries=5 \
  CMD curl -f http://localhost:${MCP_SERVER_PORT}/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
