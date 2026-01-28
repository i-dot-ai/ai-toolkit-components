#!/bin/bash
set -e

# 1. Start Qdrant in the background
# We use & to allow the script to continue to the next command
/qdrant/qdrant &
QDRANT_PID=$!

echo "Starting Qdrant (PID: $QDRANT_PID)..."

# 2. Wait for Qdrant to be ready
# It takes a few seconds for the binary to initialize and open the port
echo "Waiting for healthcheck on localhost:6333..."
MAX_RETRIES=30
COUNT=0

until curl -s http://localhost:6333/healthz > /dev/null; do
  COUNT=$((COUNT + 1))
  if [ $COUNT -ge $MAX_RETRIES ]; then
    echo "Error: Qdrant failed to start in time."
    exit 1
  fi
  sleep 1
done

echo "Qdrant is up! Running plugins..."

# Custom directory (single mount point for user customizations)
CUSTOM_DIR="/app/custom"

# Subdirectories for customizable code
SUBDIRS=("config" "plugins")

# Copy defaults to custom directory if not already present
for dir in "${SUBDIRS[@]}"; do
    mkdir -p "$CUSTOM_DIR/$dir"

    if [ -d "/app/defaults/$dir" ]; then
        for file in /app/defaults/$dir/*; do
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

# Run all Python plugins in the custom plugins directory
if ls $CUSTOM_DIR/plugins/*.py >/dev/null 2>&1; then
    echo "Running plugins..."
    for plugin in $CUSTOM_DIR/plugins/*.py; do
        [ -e "$plugin" ] || continue
        echo "Running plugin: $(basename "$plugin")"
        python3 "$plugin"
    done
else
    echo "No Python plugins found"
fi

echo "Setup complete. Keeping process alive..."

# 4. Bring the background process to the foreground
# This ensures that if Qdrant crashes, the container stops (as it should)
wait $QDRANT_PID
