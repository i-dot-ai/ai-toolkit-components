# Use official Python slim image for smaller size
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY components/vector_query/src/requirements.txt /app/defaults/requirements.txt
RUN pip install --no-cache-dir -r /app/defaults/requirements.txt

# Copy entrypoint
COPY components/vector_query/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy application source
COPY components/vector_query/src/query.py /app/

# Copy shared library
COPY common/ /app/common/

# Copy customizable defaults (will be copied to /app/custom on startup if not present)
COPY components/vector_query/src/config/ /app/defaults/config/
COPY components/vector_query/src/backends/ /app/defaults/backends/
COPY components/vector_query/src/queries/ /app/defaults/queries/

# Create custom directory (single mount point for user customization)
RUN mkdir -p /app/custom

# Default connection settings (can be overridden via VECTOR_DB_HOST / VECTOR_DB_PORT env vars)
ENV VECTOR_DB_HOST=localhost VECTOR_DB_PORT=6333

# Set PYTHONPATH so custom backends take precedence
ENV PYTHONPATH="/app/custom:/app/common:/app"

# 'run' wrapper so exec commands follow a consistent pattern across components
RUN printf '#!/bin/sh\nexec python /app/query.py "$@"\n' > /usr/local/bin/run && \
    chmod +x /usr/local/bin/run

ENTRYPOINT ["/app/entrypoint.sh"]
