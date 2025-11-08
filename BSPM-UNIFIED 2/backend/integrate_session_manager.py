# Read the file
with open('main.py', 'r') as f:
    lines = f.readlines()

# 1. Add import after websocket import
for i, line in enumerate(lines):
    if '# WebSocket' in line and 'from backend.websocket import manager as ws_manager' in lines[i+1]:
        lines.insert(i+2, '\n# Session Management\n')
        lines.insert(i+3, 'from backend.session_manager import SessionManager\n')
        break

# 2. Replace in-memory sessions declaration
for i, line in enumerate(lines):
    if 'sessions: Dict[str, Dict] = {}' in line and '# In-memory session storage' in lines[i-1]:
        lines[i-1] = '# Session storage (file-based persistence)\n'
        lines[i] = 'sessions: Dict[str, Dict] = {}  # Will be replaced by session_manager\n'
        break

# 3. Add session_manager initialization in startup event
for i, line in enumerate(lines):
    if '@app.on_event("startup")' in line:
        # Find the function body
        for j in range(i+1, min(i+20, len(lines))):
            if 'await task_queue.start()' in lines[j]:
                lines.insert(j+1, '    \n')
                lines.insert(j+2, '    # Initialize session manager\n')
                lines.insert(j+3, '    global session_manager\n')
                lines.insert(j+4, '    session_manager = SessionManager(\n')
                lines.insert(j+5, '        storage_path=os.path.join(settings.agent_memory_path, "sessions"),\n')
                lines.insert(j+6, '        expiration_hours=24\n')
                lines.insert(j+7, '    )\n')
                lines.insert(j+8, '    logger.info(f"Session manager initialized: {session_manager.get_session_count()} sessions")\n')
                break
        break

# 4. Add cleanup to shutdown event
for i, line in enumerate(lines):
    if '@app.on_event("shutdown")' in line:
        # Find the function body
        for j in range(i+1, min(i+20, len(lines))):
            if 'await task_queue.stop()' in lines[j]:
                lines.insert(j+1, '    \n')
                lines.insert(j+2, '    # Cleanup sessions\n')
                lines.insert(j+3, '    if "session_manager" in globals():\n')
                lines.insert(j+4, '        session_manager.cleanup()\n')
                lines.insert(j+5, '        logger.info("Session manager cleaned up")\n')
                break
        break

# Write back
with open('main.py', 'w') as f:
    f.writelines(lines)

print("Session manager integrated successfully")
