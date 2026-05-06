#!/bin/sh
set -e
exec python /app/src/evaluate.py "$@"
