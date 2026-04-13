# Use official Python slim image for smaller size
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY components/mcp_server/src/requirements.txt /app/defaults/requirements.txt
RUN pip install --no-cache-dir -r /app/defaults/requirements.txt

# Copy entrypoint
COPY components/mcp_server/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy application source
COPY components/mcp_server/src/server.py /app/

# Copy shared library
COPY common/ /app/common/

# Copy customisable defaults (will be copied to /app/custom on startup if not present)
COPY components/mcp_server/src/config/ /app/defaults/config/
COPY components/mcp_server/src/backends/ /app/defaults/backends/
COPY components/mcp_server/src/tools/ /app/defaults/tools/

# Create custom directory (single mount point for user customisation)
RUN mkdir -p /app/custom

# Set PYTHONPATH so custom backends/tools take precedence
ENV PYTHONPATH="/app/custom:/app/common:/app"

# Default host and port (can be overridden via MCP_SERVER_HOST / MCP_SERVER_PORT env vars)
ENV MCP_SERVER_HOST=0.0.0.0 MCP_SERVER_PORT=8080

# Run as a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
ENV PATH="/home/appuser/.local/bin:${PATH}"
USER appuser

HEALTHCHECK --interval=5s --timeout=3s --retries=5 \
  CMD curl -f http://localhost:${MCP_SERVER_PORT}/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
