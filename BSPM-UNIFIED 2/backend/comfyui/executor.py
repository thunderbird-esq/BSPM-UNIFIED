"""
ComfyUI Workflow Executor - Async execution with monitoring
Version: 3.1
Platform: Intel Mac (macOS Ventura) + Docker

Execute ComfyUI workflows and monitor progress via WebSocket/HTTP
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional
import time


async def execute_workflow(
    session: aiohttp.ClientSession,
    workflow: Dict,
    client_id: str,
    comfyui_url: str = "http://comfyui:8188",
    timeout: int = 360
) -> Dict:
    """
    Execute ComfyUI workflow and wait for completion
    
    Args:
        session: aiohttp ClientSession
        workflow: Workflow dict from workflow_builder
        client_id: Unique client identifier
        comfyui_url: ComfyUI API base URL
        timeout: Max wait time in seconds (360 = 6 minutes)
    
    Returns:
        Dict with status, frame_paths, preview_url
    
    Raises:
        RuntimeError: If generation fails or times out
    """
    
    # Submit workflow
    payload = {
        "prompt": workflow,
        "client_id": client_id
    }
    
    try:
        async with session.post(f"{comfyui_url}/prompt", json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"ComfyUI API error: {error_text}")
            
            result = await response.json()
            prompt_id = result.get("prompt_id")
            
            if not prompt_id:
                raise RuntimeError("No prompt_id returned from ComfyUI")
    
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Failed to submit workflow: {e}")
    
    # Wait for completion by polling history
    start_time = time.time()
    frame_paths = []
    preview_url = None
    
    while (time.time() - start_time) < timeout:
        try:
            async with session.get(f"{comfyui_url}/history/{prompt_id}") as response:
                if response.status == 200:
                    history = await response.json()
                    
                    if prompt_id in history:
                        outputs = history[prompt_id].get("outputs", {})
                        
                        # Collect frame outputs (nodes 9-16)
                        for node_id in range(9, 17):
                            node_str = str(node_id)
                            if node_str in outputs:
                                images = outputs[node_str].get("images", [])
                                if images:
                                    filename = images[0]["filename"]
                                    frame_paths.append(f"/output/{filename}")
                        
                        # Get preview (node 18)
                        if "18" in outputs:
                            preview_images = outputs["18"].get("images", [])
                            if preview_images:
                                preview_url = f"/output/{preview_images[0]['filename']}"
                        
                        # Check if we have all 8 frames
                        if len(frame_paths) == 8:
                            return {
                                "status": "success",
                                "prompt_id": prompt_id,
                                "frame_paths": frame_paths,
                                "preview_url": preview_url
                            }
        
        except aiohttp.ClientError:
            pass  # Continue polling
        
        await asyncio.sleep(2)  # Poll every 2 seconds
    
    # Timeout
    raise RuntimeError(f"Generation timed out after {timeout} seconds")


async def execute_spritesheet_generation(
    positive_prompt: str,
    negative_prompt: str,
    comfyui_url: str = "http://comfyui:8188",
    seed: Optional[int] = None
) -> Dict:
    """
    Complete sprite sheet generation workflow
    
    Args:
        positive_prompt: What to generate
        negative_prompt: What to avoid
        comfyui_url: ComfyUI API URL
        seed: Random seed
    
    Returns:
        Dict with status, frames, preview
    """
    from .workflow_builder import create_spritesheet_workflow
    
    # Create workflow
    workflow = create_spritesheet_workflow(
        positive_prompt=positive_prompt,
        negative_prompt=negative_prompt,
        seed=seed
    )
    
    # Generate client ID
    client_id = f"gbstudio_{int(time.time())}"
    
    # Execute
    async with aiohttp.ClientSession() as session:
        result = await execute_workflow(
            session=session,
            workflow=workflow,
            client_id=client_id,
            comfyui_url=comfyui_url
        )
    
    return result
