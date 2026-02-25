#!/bin/bash
# =============================================================================
# Component Entrypoint Template
#
# Copy this file to components/<component_name>/entrypoint.sh and update:
#
#   SUBDIRS          - list of subdirectories under /app/custom that hold
#                      user-customisable files.  "config" is always included.
#                      Add extras for any plugin directories you expose
#                      (e.g. "parsers" "backends" "tools").
#   COMPONENT_MAIN   - your main Python module (e.g. server.py)
#
# The copy-on-first-run loop at the top ensures that default files are
# present in the mounted volume on the very first container start, giving
# users a safe starting point without requiring them to supply any files
# themselves.
#
# See CONTRIBUTING.md for the full guide.
# =============================================================================
set -e

# Single mount point for all user customisations
CUSTOM_DIR="/app/custom"

# Subdirectories that hold customisable defaults.
# Add a directory here for every customisable subdirectory in src/.
SUBDIRS=("config")

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

echo "Starting component..."

# ----------------------------------------------------------------------------
# Start the component.
#
# For a persistent service, use exec so that signals (SIGTERM etc.) are
# forwarded correctly to the Python process:
#
#   exec python -u /app/COMPONENT_MAIN
#
# For a run-once task, pass through any CLI arguments supplied to
# `docker compose run`:
#
#   exec python -u /app/COMPONENT_MAIN "$@"
# ----------------------------------------------------------------------------
exec python -u /app/COMPONENT_MAIN
