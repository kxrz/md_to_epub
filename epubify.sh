#!/usr/bin/env bash
# Convenience wrapper to run md_to_epub via Docker.
# Usage:
#   ./epubify.sh myfile.md --author "Name"
#   ./epubify.sh --dir ./notes --merge --author "Name" --title "My Book"
#   ./epubify.sh --dir ./notes --output ./out --author "Name"
#
# The current directory is mounted as /data inside the container,
# so all paths are relative to where you run the script.

set -euo pipefail

IMAGE_NAME="md-to-epub"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Build image if it doesn't exist or Dockerfile is newer
if ! docker image inspect "$IMAGE_NAME" &>/dev/null || \
   [ "$SCRIPT_DIR/Dockerfile" -nt "$(docker image inspect "$IMAGE_NAME" --format '{{.Created}}' 2>/dev/null || echo 0)" ]; then
    echo "Building $IMAGE_NAME image..."
    docker build -t "$IMAGE_NAME" "$SCRIPT_DIR"
fi

docker run --rm -v "$(pwd):/data" "$IMAGE_NAME" "$@"
