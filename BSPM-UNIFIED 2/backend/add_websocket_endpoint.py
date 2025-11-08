# Read the file
with open('main.py', 'r') as f:
    content = f.read()

# Find the import section and add websocket import
import_section = "# Metrics\nfrom backend.metrics import metrics, MetricsCollector"
new_import = "# Metrics\nfrom backend.metrics import metrics, MetricsCollector\n\n# WebSocket\nfrom backend.websocket import manager as ws_manager"

content = content.replace(import_section, new_import)

# Find where to add the websocket endpoint (after /metrics endpoint)
metrics_endpoint = '''@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    metrics.update_system_metrics()
    return Response(
        content=metrics.export_metrics(),
        media_type="text/plain"
    )'''

websocket_endpoint = '''@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    metrics.update_system_metrics()
    return Response(
        content=metrics.export_metrics(),
        media_type="text/plain"
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str = "default"):
    """
    WebSocket endpoint for real-time progress updates
    
    Query params:
        session_id: Client session identifier (optional, defaults to "default")
    
    Usage:
        Connect via: ws://localhost:8000/ws?session_id=your_session_id
        
    Message types:
        - progress: Task progress updates
        - generation_progress: Sprite generation steps
        - error: Error notifications
    """
    await ws_manager.connect(websocket, session_id)
    
    try:
        # Send welcome message
        await ws_manager.send_to_session({
            "type": "connected",
            "message": f"Connected to session {session_id}",
            "session_id": session_id
        }, session_id)
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                
                # Echo back or handle client messages if needed
                message = json.loads(data) if data else {}
                
                # Handle ping/pong for keepalive
                if message.get("type") == "ping":
                    await ws_manager.send_to_session({
                        "type": "pong"
                    }, session_id)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                # Invalid JSON, ignore
                pass
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    
    finally:
        ws_manager.disconnect(websocket)'''

content = content.replace(metrics_endpoint, websocket_endpoint)

# Write back
with open('main.py', 'w') as f:
    f.write(content)

print("WebSocket endpoint added successfully")
