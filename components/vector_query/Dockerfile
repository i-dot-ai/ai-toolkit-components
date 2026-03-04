# Use official Python slim image for smaller size
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY src/requirements.txt /app/defaults/requirements.txt
RUN pip install --no-cache-dir -r /app/defaults/requirements.txt

# Copy entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy application source
COPY src/query.py src/registry.py /app/

# Copy customizable defaults (will be copied to /app/custom on startup if not present)
COPY src/config/ /app/defaults/config/
COPY src/backends/ /app/defaults/backends/
COPY src/queries/ /app/defaults/queries/

# Create custom directory (single mount point for user customization)
RUN mkdir -p /app/custom

# Set PYTHONPATH so custom backends take precedence
ENV PYTHONPATH="/app/custom:/app"

ENTRYPOINT ["/app/entrypoint.sh"]
