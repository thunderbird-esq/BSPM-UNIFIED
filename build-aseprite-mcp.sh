#!/bin/bash
# Build script for Aseprite MCP Docker service
# This script builds and validates the aseprite-mcp container

set -e

echo "=========================================="
echo "Aseprite MCP Docker Build Script"
echo "=========================================="
echo ""

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose is not installed or not in PATH"
    exit 1
fi

echo "✓ Docker and Docker Compose are available"
echo ""

# Validate docker-compose.yml syntax
echo "Validating docker-compose.intel-mac.yml syntax..."
docker compose -f docker-compose.intel-mac.yml config > /dev/null
echo "✓ YAML syntax is valid"
echo ""

# Build the container
echo "Building aseprite-mcp container..."
docker compose -f docker-compose.intel-mac.yml build aseprite-mcp

echo ""
echo "✓ Build completed successfully!"
echo ""

# Check image size
echo "Checking image size..."
IMAGE_SIZE=$(docker images gbstudio_aseprite_mcp --format "{{.Size}}")
echo "Image size: $IMAGE_SIZE"

# Verify the image was created
if docker images | grep -q "gbstudio_aseprite_mcp"; then
    echo "✓ Image was created successfully"
else
    echo "❌ Image was not created"
    exit 1
fi

echo ""
echo "=========================================="
echo "Build validation complete!"
echo "=========================================="
echo ""
echo "To start the service:"
echo "  docker compose -f docker-compose.intel-mac.yml up -d aseprite-mcp"
echo ""
echo "To view logs:"
echo "  docker compose -f docker-compose.intel-mac.yml logs -f aseprite-mcp"
echo ""
echo "To check health:"
echo "  curl http://localhost:8189/health"
