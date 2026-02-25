# =============================================================================
# Component Dockerfile Template
#
# Copy this file to components/<component_name>/Dockerfile and replace the
# SCREAMING_SNAKE_CASE placeholders with values for your component:
#
#   COMPONENT_PORT   - the port your service listens on (e.g. 8080)
#   COMPONENT_MAIN   - the main Python entry point (e.g. server.py)
#
# Remove the lines marked "# [run-once]" if your component is a persistent
# service.  Remove the lines marked "# [service]" if your component runs a
# single task and then exits (e.g. a data ingestor).
#
# See CONTRIBUTING.md for the full guide.
# =============================================================================

FROM python:3.12-slim

WORKDIR /app

# ----------------------------------------------------------------------------
# System dependencies — keep this list minimal.
# curl is required for the health check; add others only if truly necessary.
# ----------------------------------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# ----------------------------------------------------------------------------
# Python dependencies — pin versions in production images.
# ----------------------------------------------------------------------------
RUN pip install --no-cache-dir \
    pyyaml \
    requests
    # Add your dependencies here

# ----------------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------------
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# ----------------------------------------------------------------------------
# Application source
# ----------------------------------------------------------------------------
COPY src/COMPONENT_MAIN /app/

# ----------------------------------------------------------------------------
# Customisable defaults
# These are copied to /app/custom at startup if not already present,
# giving users a safe starting point they can modify in the mounted volume.
# Add a line here for each subdirectory under src/ that users may customise.
# ----------------------------------------------------------------------------
COPY src/config/ /app/defaults/config/

# Single mount point for all user customisations
RUN mkdir -p /app/custom

# ----------------------------------------------------------------------------
# Health check — required for long-running services so that dependent
# containers can use `depends_on: condition: service_healthy`.
# Remove this block if your component is a run-once task.        # [service]
# ----------------------------------------------------------------------------
HEALTHCHECK --interval=5s --timeout=3s --retries=12 \           # [service]
  CMD curl -f http://localhost:COMPONENT_PORT/health || exit 1   # [service]

EXPOSE COMPONENT_PORT                                             # [service]

ENTRYPOINT ["/app/entrypoint.sh"]
