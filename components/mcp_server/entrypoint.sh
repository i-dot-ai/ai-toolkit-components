#!/bin/bash
set -e

# Custom directory (single mount point for user customisations)
CUSTOM_DIR="/app/custom"

# Subdirectories for customisable code
SUBDIRS=("config" "backends" "tools")

# Copy defaults to custom directory if not already present
for dir in "${SUBDIRS[@]}"; do
    mkdir -p "$CUSTOM_DIR/$dir"

    if [ -d "/app/defaults/$dir" ]; then
        for file in /app/defaults/$dir/*.py /app/defaults/$dir/*.yaml; do
            [ -e "$file" ] || continue
            base_file=$(basename "$file")
            dest_file="$CUSTOM_DIR/$dir/$base_file"

            if [ ! -e "$dest_file" ]; then
                echo "Copying default: $dir/$base_file"
                cp "$file" "$dest_file"
            fi
        done
    fi
done

echo "Starting MCP server..."

exec python -u /app/server.py "$@"
