#!/usr/bin/env bash
# Build and push all component images to ghcr.io with the :latest tag.
# Usage: ./scripts/push_latest.sh [component ...]
#   With no arguments, builds all components.
#   With arguments, builds only the named components (e.g. vector_db mcp_server).

set -euo pipefail

REGISTRY="ghcr.io"
IMAGE_PREFIX="i-dot-ai/ai-toolkit"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

components=()
if [[ $# -gt 0 ]]; then
  for name in "$@"; do
    components+=("${REPO_ROOT}/components/${name}")
  done
else
  for dir in "${REPO_ROOT}"/components/*/; do
    components+=("${dir%/}")
  done
fi

for component_dir in "${components[@]}"; do
  component_name="$(basename "${component_dir}")"
  image_name="$(echo "${component_name}" | tr '_' '-')"
  full_image="${REGISTRY}/${IMAGE_PREFIX}-${image_name}:latest"

  echo "==> Building and pushing ${full_image}"
  docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --push \
    -t "${full_image}" \
    -f "${component_dir}/Dockerfile" \
    "${REPO_ROOT}"
  echo "    Pushed ${full_image}"
done

echo ""
echo "Done."
