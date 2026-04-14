# =============================================================================
# Component Dockerfile Template
#
# TODO: Copy this file to components/<component_name>/Dockerfile and work
#       through every TODO comment below.
#
# Placeholders to replace:
#   COMPONENT_NAME   - the component directory name (e.g. document_chunker)
#   COMPONENT_MAIN   - the main Python entry point filename (e.g. server.py)
#   COMPONENT_PORT   - the port your service listens on (e.g. 8080)
#
# Build context: the repo root (set in docker-compose.yaml as context: .)
# All COPY paths are therefore relative to the repo root.
#
# Lines marked "# [service]" are for persistent long-running services.
# Lines marked "# [run-once]" are for tasks that execute and exit.
# Remove whichever set does not apply to your component.
#
# See docs/contributing_components.md for the full guide.
# =============================================================================

FROM python:3.12-slim  # TODO: change base image if needed (e.g. for a non-Python service)

WORKDIR /app

# ----------------------------------------------------------------------------
# System dependencies
# curl is required for the health check; add others only if truly necessary.
# TODO: add any extra system packages your component needs
# ----------------------------------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# ----------------------------------------------------------------------------
# Python dependencies
# Add your component's dependencies to src/requirements.txt — they are
# installed here at build time and also made available to users for extension
# via the mounted volume (see entrypoint.sh).
# ----------------------------------------------------------------------------
COPY components/COMPONENT_NAME/src/requirements.txt /app/defaults/requirements.txt
RUN pip install --no-cache-dir -r /app/defaults/requirements.txt

# ----------------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------------
COPY components/COMPONENT_NAME/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# ----------------------------------------------------------------------------
# Application source
# TODO: replace COMPONENT_MAIN with your actual filename (e.g. server.py)
# ----------------------------------------------------------------------------
COPY components/COMPONENT_NAME/src/COMPONENT_MAIN /app/

# ----------------------------------------------------------------------------
# Shared library (provides PluginRegistry and other shared utilities)
# TODO: remove this block if your component does not use extensibility extensions
# ----------------------------------------------------------------------------
COPY common/ /app/common/

# ----------------------------------------------------------------------------
# Customisable defaults
# These are copied to /app/custom at startup if not already present.
# TODO: remove whichever of the two plugin lines does not apply:
#   plugins/    → startup scripts, run once by the entrypoint after service start
#   extensions/ → extensibility classes, auto-discovered by PluginRegistry at runtime
# TODO: add extra COPY lines for any additional customisable subdirectories
# ----------------------------------------------------------------------------
COPY components/COMPONENT_NAME/src/config/ /app/defaults/config/
COPY components/COMPONENT_NAME/src/plugins/ /app/defaults/plugins/        # TODO: remove if not using startup scripts
COPY components/COMPONENT_NAME/src/extensions/ /app/defaults/extensions/  # TODO: remove if not using extensibility extensions

# Single mount point for all user customisations
RUN mkdir -p /app/custom

# Ensure custom extensions take precedence, then shared lib, then app root
# TODO: remove /app/common from PYTHONPATH if your component does not use extensibility extensions
ENV PYTHONPATH="/app/custom:/app/common:/app"

# Run as a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
ENV PATH="/home/appuser/.local/bin:${PATH}"
USER appuser

# ----------------------------------------------------------------------------
# Health check — required for HTTP services so that dependent containers can
# use `depends_on: condition: service_healthy`.
# TODO: replace COMPONENT_PORT with your actual port number
# TODO: remove this entire block for CLI components (no HTTP endpoint)
# ----------------------------------------------------------------------------
HEALTHCHECK --interval=5s --timeout=3s --retries=12 \
  CMD curl -f http://localhost:COMPONENT_PORT/health || exit 1

EXPOSE COMPONENT_PORT  # TODO: replace with your actual port number

# ----------------------------------------------------------------------------
# 'run' wrapper — CLI components only.
# Lets users invoke the component with: docker compose exec COMPONENT_NAME run <args>
# TODO: replace COMPONENT_MAIN with your actual filename (e.g. ingestor.py)
# TODO: remove this block for HTTP services (they are invoked via their API, not exec)
# ----------------------------------------------------------------------------
# RUN printf '#!/bin/sh\nexec python /app/COMPONENT_MAIN "$@"\n' > /usr/local/bin/run && \
#     chmod +x /usr/local/bin/run

ENTRYPOINT ["/app/entrypoint.sh"]
