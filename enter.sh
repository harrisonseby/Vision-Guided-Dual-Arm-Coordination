#!/bin/bash

CONTAINER_NAME="vision-guided-dual-arm-coordination-dev"

# Check if container is running
if [ ! "$(docker ps -q -f name=^${CONTAINER_NAME}$)" ]; then
    echo "Error: Container '${CONTAINER_NAME}' is not running."
    echo "Start it first with: ./devel.sh"
    exit 1
fi

echo "Entering container '${CONTAINER_NAME}'..."
docker exec -it ${CONTAINER_NAME} bash
