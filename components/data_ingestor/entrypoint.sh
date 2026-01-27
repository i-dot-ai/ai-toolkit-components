#!/bin/bash
set -e

# Runtime directories where user can customize
RUNTIME_DIRS=("config" "parsers" "embedders")

# Copy defaults to runtime directories
# Files are only copied if they don't already exist (preserves user customizations)
for dir in "${RUNTIME_DIRS[@]}"; do
    mkdir -p "/app/$dir"

    if [ -d "/app/defaults/$dir" ]; then
        echo "Processing default $dir files..."
        for file in /app/defaults/$dir/*; do
            [ -e "$file" ] || continue
            base_file=$(basename "$file")
            dest_file="/app/$dir/$base_file"

            if [ ! -e "$dest_file" ]; then
                echo "Copying default: $dir/$base_file"
                cp -r "$file" "$dest_file"
            fi
        done
    fi
done

# Copy ingestor.py to runtime location
if [ ! -f "/app/ingestor.py" ]; then
    cp /app/defaults/ingestor.py /app/ingestor.py
fi

echo "Starting data ingestor..."

# Run the main ingestor application from runtime directory
exec python -u /app/ingestor.py "$@"
