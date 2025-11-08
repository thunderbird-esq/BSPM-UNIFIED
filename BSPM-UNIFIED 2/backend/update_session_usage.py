# Read the file
with open('main.py', 'r') as f:
    content = f.read()

# Replace session storage in handle_prompt
old_session_store = """    # Store preset in session
    if session_id not in sessions:
        sessions[session_id] = {}
    sessions[session_id]['preset'] = preset"""

new_session_store = """    # Store preset in session
    if 'session_manager' in globals():
        session_manager.update_session(session_id, {'preset': preset})
    else:
        # Fallback to in-memory
        if session_id not in sessions:
            sessions[session_id] = {}
        sessions[session_id]['preset'] = preset"""

content = content.replace(old_session_store, new_session_store)

# Replace session retrieval in handle_execution
old_session_get = """    # Get preset from session if available
    preset = sessions.get(request.session_id, {}).get('preset')"""

new_session_get = """    # Get preset from session if available
    if 'session_manager' in globals():
        session_data = session_manager.get_session(request.session_id)
        preset = session_data.get('data', {}).get('preset') if session_data else None
    else:
        preset = sessions.get(request.session_id, {}).get('preset')"""

content = content.replace(old_session_get, new_session_get)

# Write back
with open('main.py', 'w') as f:
    f.write(content)

print("Session usage updated successfully")
