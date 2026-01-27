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
    requests \
    beautifulsoup4 \
    pyyaml \
    lxml \
    qdrant-client \
    sentence-transformers

# Copy entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy source as defaults (will be copied to runtime dirs on startup)
COPY src/ /app/defaults/

# Create runtime directories (these are the mount points for user customization)
RUN mkdir -p /app/config /app/parsers /app/embedders /app/output

# Set PYTHONPATH to use runtime directories
ENV PYTHONPATH="/app"

# Health check - verify the process is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "python.*ingestor" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
