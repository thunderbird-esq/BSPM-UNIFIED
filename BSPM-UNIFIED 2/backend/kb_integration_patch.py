import sys

# Read the file
with open('main.py', 'r') as f:
    lines = f.readlines()

# Find and replace the KB integration section
new_section = '''    req_logger.info(f"Processing prompt: {request.message[:50]}...")

    # Auto-detect style preset if not specified
    if not request.preset:
        preset = get_optimal_preset_for_description(request.message)
        req_logger.info(f"Auto-selected preset: {preset.value}")
    else:
        preset = request.preset

    # Store preset in session
    if session_id not in sessions:
        sessions[session_id] = {}
    sessions[session_id]['preset'] = preset

    recent_context = get_recent_conversation_context(session_id)

    # Search knowledge base for relevant context
    kb_context = "No relevant documentation found."
    try:
        from backend.memory.knowledge_base import KnowledgeBase

        # Initialize KB if not already done
        kb = KnowledgeBase(
            vectorstore_path=settings.vectorstore_path,
            embedding_url=settings.ollama_embeddings_url,
            embedding_model=settings.embedding_model
        )

        # Search for relevant documentation
        search_results = kb.search(
            query=request.message,
            k=3,
            filter_type="project_doc"
        )

        # Filter by relevance threshold (min similarity 0.7)
        # Note: FAISS returns L2 distance, lower is better
        # For normalized vectors, L2 distance of ~1.0 = similarity of ~0.7
        relevant_results = [r for r in search_results if r['score'] < 1.5]

        if relevant_results:
            # Format KB results for LLM consumption
            kb_parts = ["## Relevant Documentation:"]
            for i, result in enumerate(relevant_results, 1):
                doc_type = result['metadata'].get('doc_type', 'unknown')
                kb_parts.append(f"\\n### Document {i} ({doc_type}):")
                kb_parts.append(result['content'][:400] + "...")
            kb_context = "\\n".join(kb_parts)
            req_logger.info(f"Found {len(relevant_results)} relevant KB documents")
        else:
            req_logger.info("No relevant KB documents found above threshold")

    except Exception as e:
        req_logger.warning(f"KB search failed: {e}, continuing without KB context")
        kb_context = "No relevant documentation found."

    full_prompt = PM_AGENT_PROMPT.format(
        recent_context=recent_context,
        kb_context=kb_context,
        user_message=request.message
    )
'''

# Find the section to replace (lines 772-786)
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if 'req_logger.info(f"Processing prompt: {request.message[:50]}...")' in line:
        start_idx = i
    if start_idx is not None and 'user_message=request.message' in line and ')' in lines[i+1] if i+1 < len(lines) else False:
        end_idx = i + 2
        break

if start_idx is not None and end_idx is not None:
    # Replace the section
    lines[start_idx:end_idx] = [new_section + '\n']
    
    # Write back
    with open('main.py', 'w') as f:
        f.writelines(lines)
    
    print(f"Successfully patched lines {start_idx+1}-{end_idx}")
else:
    print("Could not find the section to replace")
    sys.exit(1)
