#!/bin/bash

# Allow Docker to access X server
xhost +local:docker > /dev/null 2>&1

echo "Starting container..."
docker compose up -d

echo "Container is running. Use './enter.sh' to access it."
