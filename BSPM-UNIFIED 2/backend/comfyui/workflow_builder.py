"""
ComfyUI Workflow Builder - Programmatic Workflow Construction
Version: 3.1
Platform: Intel Mac (macOS Ventura) + Docker

Generates ComfyUI workflow JSON from parameters
"""

import random
from typing import Dict, Optional


def create_spritesheet_workflow(
    positive_prompt: str,
    negative_prompt: str,
    seed: Optional[int] = None,
    steps: int = 20,
    cfg: float = 8.0,
    width: int = 256,
    height: int = 256
) -> Dict:
    """
    Create ComfyUI workflow for 8-frame sprite sheet generation
    
    Args:
        positive_prompt: What to generate
        negative_prompt: What to avoid
        seed: Random seed (None = random)
        steps: Sampling steps (20 for Intel Mac CPU)
        cfg: CFG scale (8.0 = good for sprite sheets)
        width: Latent width (256 = 8x32 grid)
        height: Latent height (256 = 8x32 grid)
    
    Returns:
        Complete workflow dict ready for ComfyUI API
    """
    
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    
    # Enhance prompts for sprite sheet generation
    enhanced_positive = (
        f"{positive_prompt}, sprite sheet, multiple poses, character turnaround, "
        f"animation frames, 8 frames grid, pixel art, game boy color, 32x32 pixels"
    )
    
    enhanced_negative = (
        f"{negative_prompt}, inconsistent style, different characters, blurry, "
        f"photo realistic, 3d render, modern graphics, high resolution"
    )
    
    workflow = {
        # Node 1: Load SDXL base model
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "sd_xl_base_1.0.safetensors"
            }
        },
        
        # Node 2: Apply pixel art LoRA
        "2": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "pixel-art-xl-v1.1.safetensors",
                "strength_model": 1.0,
                "strength_clip": 1.0,
                "model": ["1", 0],
                "clip": ["1", 1]
            }
        },
        
        # Node 3: Encode positive prompt
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": enhanced_positive,
                "clip": ["2", 1]
            }
        },
        
        # Node 4: Encode negative prompt
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": enhanced_negative,
                "clip": ["2", 1]
            }
        },
        
        # Node 5: Create empty latent
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            }
        },
        
        # Node 6: Sample latent (main generation)
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler_ancestral",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["2", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0]
            }
        },
        
        # Node 7: Decode latent to image
        "7": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["6", 0],
                "vae": ["1", 2]
            }
        },
        
        # Node 8: Split into 32x32 tiles
        "8": {
            "class_type": "DynamicTileSplit",
            "inputs": {
                "image": ["7", 0],
                "tile_width": 32,
                "tile_height": 32,
                "overlap": 0,
                "offset": 0
            }
        }
    }
    
    # Nodes 9-16: Save individual frames
    for i in range(8):
        workflow[str(9 + i)] = {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": f"sprite_frame_{i}",
                "images": ["8", 0, i]
            }
        }
    
    # Node 17: Merge tiles for preview
    workflow["17"] = {
        "class_type": "DynamicTileMerge",
        "inputs": {
            "images": ["8", 0],
            "tile_calc": ["8", 1],
            "blend": 0
        }
    }
    
    # Node 18: Save merged preview
    workflow["18"] = {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "sprite_sheet_preview",
            "images": ["17", 0]
        }
    }
    
    return workflow


def create_background_workflow(
    positive_prompt: str,
    negative_prompt: str,
    seed: Optional[int] = None,
    steps: int = 20,
    cfg: float = 7.0
) -> Dict:
    """
    Create workflow for 160x144 background generation
    
    Args:
        positive_prompt: Scene description
        negative_prompt: What to avoid
        seed: Random seed
        steps: Sampling steps
        cfg: CFG scale
    
    Returns:
        Workflow dict
    """
    
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    
    enhanced_positive = (
        f"{positive_prompt}, game boy color background, pixel art, "
        f"160x144 pixels, retro game scene, simple details"
    )
    
    enhanced_negative = (
        f"{negative_prompt}, blurry, photo realistic, modern graphics, "
        f"complex details, high resolution"
    )
    
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}
        },
        "2": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "pixel-art-xl-v1.1.safetensors",
                "strength_model": 1.0,
                "strength_clip": 1.0,
                "model": ["1", 0],
                "clip": ["1", 1]
            }
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": enhanced_positive,
                "clip": ["2", 1]
            }
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": enhanced_negative,
                "clip": ["2", 1]
            }
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 160,
                "height": 144,
                "batch_size": 1
            }
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler_ancestral",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["2", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0]
            }
        },
        "7": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["6", 0],
                "vae": ["1", 2]
            }
        },
        "8": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "background",
                "images": ["7", 0]
            }
        }
    }
    
    return workflow
