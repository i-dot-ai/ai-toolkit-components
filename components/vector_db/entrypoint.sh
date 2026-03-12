#!/bin/bash
set -e

# Custom directory (single mount point for user customizations)
CUSTOM_DIR="/app/custom"

# Subdirectories for customizable code
SUBDIRS=("config" "plugins")

# Copy defaults to custom directory if not already present
for dir in "${SUBDIRS[@]}"; do
    mkdir -p "$CUSTOM_DIR/$dir"

    if [ -d "/app/defaults/$dir" ]; then
        for file in /app/defaults/$dir/*.py /app/defaults/$dir/*.yaml; do
            [ -e "$file" ] || continue
            base_file=$(basename "$file")
            dest_file="$CUSTOM_DIR/$dir/$base_file"

            if [ ! -f "$dest_file" ]; then
                echo "Copying default: $dir/$base_file"
                cp "$file" "$dest_file"
            fi
        done
    fi
done

# Load config options from config.yaml and export as Qdrant environment variables
# Qdrant uses the QDRANT__<SECTION>__<KEY> format (double underscores)
CONFIG_FILE="$CUSTOM_DIR/config/config.yaml"
if [ -f "$CONFIG_FILE" ]; then
    echo "Loading config from $CONFIG_FILE..."
    eval "$(python3 /app/load_config.py "$CONFIG_FILE")"
    echo "Config loaded."
else
    echo "No config file found at $CONFIG_FILE, using defaults."
fi

# Apply host/port configuration (env vars take precedence over config.yaml)
export QDRANT__SERVICE__HOST=${VECTOR_DB_BIND_HOST:-0.0.0.0}
export QDRANT__SERVICE__HTTP_PORT=${VECTOR_DB_HTTP_PORT:-6333}
export QDRANT__SERVICE__GRPC_PORT=${VECTOR_DB_GRPC_PORT:-6334}

# Start Qdrant in the background (after config is loaded so env vars take effect)
/qdrant/qdrant &
QDRANT_PID=$!

echo "Starting Qdrant (PID: $QDRANT_PID)..."

# Wait for Qdrant to be ready
echo "Waiting for healthcheck on localhost:${VECTOR_DB_HTTP_PORT:-6333}..."
MAX_RETRIES=30
COUNT=0

until curl -s http://localhost:${VECTOR_DB_HTTP_PORT:-6333}/healthz > /dev/null; do
  COUNT=$((COUNT + 1))
  if [ $COUNT -ge $MAX_RETRIES ]; then
    echo "Error: Qdrant failed to start in time."
    exit 1
  fi
  sleep 1
done

echo "Qdrant is up!"

# Install any extra packages added to the custom requirements file
if [ ! -f "$CUSTOM_DIR/requirements.txt" ]; then
    echo "Copying default: requirements.txt"
    cp /app/defaults/requirements.txt "$CUSTOM_DIR/requirements.txt"
else
    echo "Requirements updated so installing packages..."
    pip install --quiet --no-cache-dir -r "$CUSTOM_DIR/requirements.txt"
fi

# Run all Python plugins in the custom plugins directory
if ls "$CUSTOM_DIR/plugins/"*.py >/dev/null 2>&1; then
    echo "Running plugins..."
    for plugin in "$CUSTOM_DIR/plugins/"*.py; do
        [ -e "$plugin" ] || continue
        echo "Running plugin: $(basename "$plugin")"
        python3 "$plugin" || echo "Warning: plugin $(basename "$plugin") failed, continuing..."
    done
else
    echo "No Python plugins found"
fi

echo "Setup complete. Keeping process alive..."

# Forward SIGTERM/SIGINT to Qdrant so it shuts down cleanly on docker stop
trap 'kill -SIGTERM $QDRANT_PID' SIGTERM SIGINT

# Bring the background process to the foreground
wait $QDRANT_PID
