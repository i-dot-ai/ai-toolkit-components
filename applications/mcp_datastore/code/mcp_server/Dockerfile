FROM ghcr.io/i-dot-ai/ai-toolkit-mcp-server:latest

# Bake custom tools, backends, and config into the image.
# The entrypoint will not overwrite files already present in /app/custom/,
# so these take precedence over the built-in defaults.
COPY tools/    /app/custom/tools/
COPY backends/ /app/custom/backends/
COPY config/   /app/custom/config/

# Pre-install any extra dependencies so container startup is fast.
# Uncomment and edit if your custom code requires additional packages.
# COPY requirements.txt /app/custom/requirements.txt
# RUN pip install --no-cache-dir -r /app/custom/requirements.txt
