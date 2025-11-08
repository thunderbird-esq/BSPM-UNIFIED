#!/bin/bash
# Quick diagnostic for test failures

API_KEY="test-api-key-49a07b1d54218c8df192114e5eb35dcd"
BACKEND_URL="http://localhost:8000"

echo "=== Diagnostic Tests ==="
echo ""

echo "1. Testing /execute with empty plan (getting 422):"
curl -v -X POST $BACKEND_URL/api/v1/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "plan": []}'  2>&1 | grep -E "HTTP|{"

echo ""
echo "2. Testing /execute with valid task:"
curl -s -X POST $BACKEND_URL/api/v1/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "plan": [{
      "department": "Art",
      "task": "Test task",
      "details": {}
    }]
  }' | python3 -m json.tool

echo ""
echo "3. Testing KB upload (getting 403):"
curl -v -X POST $BACKEND_URL/api/v1/admin/kb/upload \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.md", "content": "Test"}' 2>&1 | grep -E "HTTP|{"

echo ""
echo "4. Testing WebSocket (getting 404):"
curl -v -X GET $BACKEND_URL/ws?session_id=test 2>&1 | grep "HTTP"

echo ""
echo "5. Checking if WebSocket endpoint exists:"
curl -s $BACKEND_URL/docs | grep -i websocket || echo "Not in docs"

echo ""
echo "6. Testing PM Agent (actually works):"
curl -s -X POST $BACKEND_URL/api/v1/prompt \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "session_id": "test"}' | python3 -c "import sys, json; data=json.load(sys.stdin); print('✓ Has message field' if 'message' in data else '✗ No message field'); print(f'Response fields: {list(data.keys())}')"

