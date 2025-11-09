#!/bin/bash

echo "🧪 Testing GBStudio Automation Hub"
echo ""

echo "1. Health check..."
curl -s http://localhost:8000/health | jq -r '.backend, .services.ollama.status, .services.comfyui.status'

echo ""
echo "2. Presets available..."
curl -s http://localhost:8000/api/v1/presets | jq -r '.presets[]'

echo ""
echo "3. Test PM agent..."
curl -s -X POST http://localhost:8000/api/v1/prompt \
  -H 'Content-Type: application/json' \
  -d '{"message": "create a pixel art knight sprite"}' | jq -r '.message'

echo ""
echo "✅ Tests complete"
