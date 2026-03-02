#!/bin/bash
# =============================================================================
# Component Entrypoint Template
#
# TODO: Copy this file to components/<component_name>/entrypoint.sh and work
#       through every TODO comment below.
#
# See docs/contributing.md for the full guide.
# =============================================================================
set -e

# TODO: Set to the name of your component's main Python file (e.g. server.py)
COMPONENT_MAIN="COMPONENT_MAIN"

# Single mount point for all user customisations
CUSTOM_DIR="/app/custom"

# TODO: list every subdirectory under src/ that holds user-customisable files.
# "config" is always present.
# "plugins"    → startup scripts (run once after service start); remove if not used
# "extensions" → extensibility classes (auto-discovered by PluginRegistry); remove if not used
SUBDIRS=("config" "plugins" "extensions")

# ----------------------------------------------------------------------------
# Copy defaults into the mounted volume on first run.
# Files that already exist are left untouched so user edits are preserved.
# ----------------------------------------------------------------------------
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

# Install any extra packages added to the custom requirements file
if [ ! -f "$CUSTOM_DIR/requirements.txt" ]; then
    echo "Copying default: requirements.txt"
    cp /app/defaults/requirements.txt "$CUSTOM_DIR/requirements.txt"
fi
pip install --quiet -r "$CUSTOM_DIR/requirements.txt"

# ----------------------------------------------------------------------------
# TODO: If your component uses startup scripts, start your service in the
# background first, wait for it to be ready, then run the scripts below.
# Remove this block entirely if you are not using the startup script pattern.
#
# if ls "$CUSTOM_DIR/plugins/"*.py > /dev/null 2>&1; then
#     echo "Running startup plugins..."
#     for plugin in "$CUSTOM_DIR/plugins/"*.py; do
#         echo "Running plugin: $(basename "$plugin")"
#         python3 "$plugin"
#     done
# fi
# ----------------------------------------------------------------------------

echo "Starting ${COMPONENT_MAIN}..."

# ----------------------------------------------------------------------------
# TODO: Choose one of the two exec lines below and delete the other.
#
# For a persistent service, signals (SIGTERM etc.) are forwarded correctly:
exec python -u /app/${COMPONENT_MAIN}
#
# For a run-once task, CLI arguments from `docker compose run` are passed through:
# exec python -u /app/${COMPONENT_MAIN} "$@"
# ----------------------------------------------------------------------------
