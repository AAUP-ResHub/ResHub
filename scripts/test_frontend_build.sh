#!/bin/bash
# Frontend Docker Build Testing Script
# Tests the frontend build pipeline using Docker Compose

# Print commands as they are executed
set -x

echo "=== Testing Frontend Build Pipeline ==="

# Navigate to project root directory
cd "$(dirname "$0")/.."

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed"
    exit 1
fi

# Check if the frontend.Dockerfile exists
if [ ! -f "./docker/frontend.Dockerfile" ]; then
    echo "Error: docker/frontend.Dockerfile not found"
    exit 1
fi

# Check if the docker-compose.frontend.yml exists
if [ ! -f "./docker-compose.frontend.yml" ]; then
    echo "Error: docker-compose.frontend.yml not found"
    exit 1
fi

echo "Running frontend build with Docker Compose..."

# Build the frontend service
docker-compose -f docker-compose.yml -f docker-compose.frontend.yml build frontend

# Check if build succeeded
if [ $? -ne 0 ]; then
    echo "Error: Frontend build failed"
    exit 1
fi

echo "Frontend build successful."

# Test dev server mode (optional)
echo "Testing development mode (press Ctrl+C to stop)..."
docker-compose -f docker-compose.yml -f docker-compose.frontend.yml up frontend

# Exit with success
echo "Frontend build pipeline test completed successfully."
exit 0
