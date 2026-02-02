#!/bin/bash
# Stop all osworld worker containers
#
# Usage:
#   ./scripts/stop_workers.sh [num_workers]

set -e

NUM_WORKERS=${1:-5}

# Auto-detect runtime
if command -v podman &> /dev/null; then
    RUNTIME="podman"
elif command -v docker &> /dev/null; then
    RUNTIME="docker"
else
    echo "Error: Neither podman nor docker found"
    exit 1
fi

echo "Stopping $NUM_WORKERS workers..."

for i in $(seq 0 $((NUM_WORKERS - 1))); do
    CONTAINER_NAME="osworld-$i"
    echo "Stopping $CONTAINER_NAME..."
    $RUNTIME rm -f "$CONTAINER_NAME" 2>/dev/null || true
done

echo "Done."
