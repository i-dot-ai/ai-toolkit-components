FROM ghcr.io/i-dot-ai/ai-toolkit-vector-db:latest

# Bake custom plugins and config into the image.
# The entrypoint will not overwrite files already present in /app/custom/,
# so these take precedence over the built-in defaults.
COPY plugins/ /app/custom/plugins/
COPY config/  /app/custom/config/
