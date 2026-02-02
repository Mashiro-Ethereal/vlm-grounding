#!/bin/bash
# Start multiple osworld containers for concurrent SFT data collection
#
# Usage:
#   ./scripts/start_workers.sh [num_workers]
#   ./scripts/start_workers.sh 5    # Start 5 workers

set -e

NUM_WORKERS=${1:-5}
BASE_PORT=8080
IMAGE="localhost/osworld-desktopd:latest"

# Auto-detect runtime
if command -v podman &> /dev/null; then
    RUNTIME="podman"
elif command -v docker &> /dev/null; then
    RUNTIME="docker"
else
    echo "Error: Neither podman nor docker found"
    exit 1
fi

echo "Using runtime: $RUNTIME"
echo "Starting $NUM_WORKERS workers..."

for i in $(seq 0 $((NUM_WORKERS - 1))); do
    CONTAINER_NAME="osworld-$i"
    DESKTOPD_PORT=$((BASE_PORT + i * 10))
    DOM_API_PORT=$((BASE_PORT + 42 + i * 10))

    # Stop existing container if running
    $RUNTIME rm -f "$CONTAINER_NAME" 2>/dev/null || true

    echo "Starting $CONTAINER_NAME (ports: $DESKTOPD_PORT, $DOM_API_PORT)..."

    $RUNTIME run -d \
        --name "$CONTAINER_NAME" \
        -p "$DESKTOPD_PORT:8080" \
        -p "$DOM_API_PORT:8122" \
        "$IMAGE" \
        /boot.sh
done

echo ""
echo "Waiting for containers to boot (60s)..."
sleep 60

echo ""
echo "Container status:"
for i in $(seq 0 $((NUM_WORKERS - 1))); do
    CONTAINER_NAME="osworld-$i"
    DESKTOPD_PORT=$((BASE_PORT + i * 10))

    # Check if container is responding
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$DESKTOPD_PORT/api/v1/screenshot" 2>/dev/null | grep -q "200"; then
        echo "  $CONTAINER_NAME: READY (port $DESKTOPD_PORT)"
    else
        echo "  $CONTAINER_NAME: NOT READY (port $DESKTOPD_PORT)"
    fi
done

echo ""
echo "To collect data:"
echo "  python scripts/collect_sft_data_concurrent.py -o ./dataset/sft_100 -n 100 -w $NUM_WORKERS"
echo ""
echo "To stop all workers:"
echo "  ./scripts/stop_workers.sh $NUM_WORKERS"
