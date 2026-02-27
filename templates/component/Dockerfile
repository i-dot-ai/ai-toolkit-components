# =============================================================================
# Component Dockerfile Template
#
# TODO: Copy this file to components/<component_name>/Dockerfile and work
#       through every TODO comment below.
#
# Placeholders to replace:
#   COMPONENT_MAIN   - the main Python entry point filename (e.g. server.py)
#   COMPONENT_PORT   - the port your service listens on (e.g. 8080)
#
# Lines marked "# [service]" are for persistent long-running services.
# Lines marked "# [run-once]" are for tasks that execute and exit.
# Remove whichever set does not apply to your component.
#
# See docs/contributing.md for the full guide.
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
COPY src/requirements.txt /app/defaults/requirements.txt
RUN pip install --no-cache-dir -r /app/defaults/requirements.txt

# ----------------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------------
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# ----------------------------------------------------------------------------
# Application source
# TODO: replace COMPONENT_MAIN with your actual filename (e.g. server.py)
# TODO: remove the registry.py line if your component does not use plugins
# ----------------------------------------------------------------------------
COPY src/COMPONENT_MAIN /app/
COPY src/registry.py /app/  # TODO: remove if not using extensibility extensions

# ----------------------------------------------------------------------------
# Customisable defaults
# These are copied to /app/custom at startup if not already present.
# TODO: remove whichever of the two plugin lines does not apply:
#   plugins/    → startup scripts, run once by the entrypoint after service start
#   extensions/ → extensibility classes, auto-discovered by PluginRegistry at runtime
# TODO: add extra COPY lines for any additional customisable subdirectories
# ----------------------------------------------------------------------------
COPY src/config/ /app/defaults/config/
COPY src/requirements.txt /app/defaults/requirements.txt
COPY src/plugins/ /app/defaults/plugins/        # TODO: remove if not using startup scripts
COPY src/extensions/ /app/defaults/extensions/  # TODO: remove if not using extensibility extensions

# Single mount point for all user customisations
RUN mkdir -p /app/custom

# Ensure custom extensions take precedence over the bundled defaults at import time
# TODO: remove this line if your component does not use extensibility extensions
ENV PYTHONPATH="/app/custom:/app"

# ----------------------------------------------------------------------------
# Health check — required for long-running services so that dependent
# containers can use `depends_on: condition: service_healthy`.
# TODO: replace COMPONENT_PORT with your actual port number
# TODO: remove this entire block if your component is a run-once task  [run-once]
# ----------------------------------------------------------------------------
HEALTHCHECK --interval=5s --timeout=3s --retries=12 \           # [service]
  CMD curl -f http://localhost:COMPONENT_PORT/health || exit 1   # [service]

EXPOSE COMPONENT_PORT  # TODO: replace with your actual port number  # [service]

ENTRYPOINT ["/app/entrypoint.sh"]
