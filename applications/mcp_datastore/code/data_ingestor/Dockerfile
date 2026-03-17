FROM ghcr.io/i-dot-ai/ai-toolkit-data-ingestor:latest

# Bake custom parsers, embedders, and config into the image.
# The entrypoint will not overwrite files already present in /app/custom/,
# so these take precedence over the built-in defaults.
COPY parsers/  /app/custom/parsers/
COPY embedders/ /app/custom/embedders/
COPY config/   /app/custom/config/

# Pre-install any extra dependencies so container startup is fast.
# Uncomment and edit if your custom code requires additional packages.
# COPY requirements.txt /app/custom/requirements.txt
# RUN pip install --no-cache-dir -r /app/custom/requirements.txt
