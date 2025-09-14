#!/usr/bin/env python3
"""
vPrompt Integration with ComfyUI
Integrates vPrompt JSON output with ComfyUI image generation
"""

import json
import sys
import os
try:
    from .comfyui_client import generate_image
except ImportError:
    try:
        from comfyui_client import generate_image
    except ImportError:
        print("ComfyUI client not available, using mock mode")
        generate_image = None
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def json_to_prompt(vprompt_json):
    """Convert vPrompt JSON to a ComfyUI prompt"""
    if isinstance(vprompt_json, str):
        try:
            vprompt_json = json.loads(vprompt_json)
        except json.JSONDecodeError:
            return None, None
    
    # Extract relevant fields for image generation
    scene = vprompt_json.get('Scene', '')
    ambiance = vprompt_json.get('ambiance_or_mood', '')
    location = vprompt_json.get('Location', '')
    visual_style = vprompt_json.get('Visual style', '')
    lighting = vprompt_json.get('lighting', '')
    extra_desc = vprompt_json.get('extra_desc', '')
    
    # Build positive prompt
    positive_parts = []
    
    # Handle Scene field - it can be dict or string
    if scene:
        if isinstance(scene, dict):
            # Extract description and elements - handle both uppercase and lowercase keys
            if 'Description' in scene:
                positive_parts.append(scene['Description'])
            elif 'description' in scene:
                positive_parts.append(scene['description'])
            if 'elements' in scene and isinstance(scene['elements'], list):
                positive_parts.extend([str(elem) for elem in scene['elements']])
        else:
            positive_parts.append(str(scene))
    
    # Handle Location field - it can be dict or string
    if location:
        if isinstance(location, dict):
            if 'setting' in location:
                positive_parts.append(f"set in {location['setting']}")
            elif 'specific_location' in location:
                positive_parts.append(f"set in {location['specific_location']}")
        else:
            positive_parts.append(f"set in {str(location)}")
    
    # Handle ambiance
    if ambiance:
        positive_parts.append(f"with {str(ambiance)} atmosphere")
    
    # Handle Visual style field - it can be dict or string
    if visual_style:
        if isinstance(visual_style, dict):
            if 'art_style' in visual_style:
                positive_parts.append(f"in {visual_style['art_style']} style")
        else:
            positive_parts.append(f"in {str(visual_style)} style")
    
    # Handle lighting field - it can be dict or string
    if lighting:
        if isinstance(lighting, dict):
            if 'type' in lighting:
                positive_parts.append(f"featuring {lighting['type']}")
            if 'characteristics' in lighting:
                positive_parts.append(lighting['characteristics'])
        else:
            positive_parts.append(f"featuring {str(lighting)}")
    
    # Handle extra description
    if extra_desc:
        positive_parts.append(str(extra_desc))
    
    # Add quality terms
    positive_parts.extend([
        "highly detailed",
        "professional quality",
        "8k resolution",
        "masterpiece"
    ])
    
    positive_prompt = ", ".join(positive_parts)
    
    # Standard negative prompt
    negative_prompt = "blurry, low quality, bad anatomy, distorted, amateur, ugly, poor lighting, bad composition"
    
    return positive_prompt, negative_prompt

def generate_from_vprompt_json(json_file, output_dir="./vprompt_output", seed=None):
    """Generate image from vPrompt JSON file"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            vprompt_data = json.load(f)
        
        positive, negative = json_to_prompt(vprompt_data)
        
        if not positive:
            print("❌ Failed to extract prompt from JSON")
            return None
        
        print(f"📝 Generated prompt:")
        print(f"   Positive: {positive[:100]}...")
        print(f"   Negative: {negative}")
        
        # Generate image
        if generate_image is None:
            print("❌ ComfyUI not available, cannot generate images")
            return None
            
        images = generate_image(
            prompt_text=positive,
            negative_prompt=negative or "",
            output_dir=output_dir,
            seed=seed
        )
        
        return images
        
    except Exception as e:
        print(f"❌ Error processing vPrompt JSON: {e}")
        return None

def generate_from_vprompt_dict(vprompt_dict, output_dir="./vprompt_output", seed=None, progress_callback=None, server_address=None, port=None):
    """Generate image from vPrompt dictionary"""
    try:
        positive, negative = json_to_prompt(vprompt_dict)
        
        if not positive:
            print("❌ Failed to extract prompt from dictionary")
            return None
        
        print(f"📝 Generated prompt from vPrompt data:")
        print(f"   Positive: {positive[:100]}...")
        
        # Generate image
        if generate_image is None:
            print("❌ ComfyUI not available, cannot generate images")
            return None
            
        images = generate_image(
            prompt_text=positive,
            negative_prompt=negative or "",
            output_dir=output_dir,
            seed=seed,
            progress_callback=progress_callback,
            server_address=server_address,
            port=port
        )
        
        return images
        
    except Exception as e:
        print(f"❌ Error processing vPrompt dictionary: {e}")
        return None

def main():
    """CLI interface"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python vprompt_integration.py <vprompt_json_file>")
        print("  python vprompt_integration.py --test")
        return
    
    if sys.argv[1] == "--test":
        # Test with sample vPrompt JSON
        sample_json = {
            "Scene": "A magical forest clearing at twilight",
            "ambiance_or_mood": "mystical and enchanting",
            "Location": "ancient woodland with towering trees",
            "Visual style": "fantasy art with ethereal lighting",
            "lighting": "soft moonbeams filtering through leaves",
            "extra_desc": "fireflies dancing, moss-covered stones, magical atmosphere"
        }
        
        print("🧪 Testing with sample vPrompt JSON...")
        images = generate_from_vprompt_dict(sample_json, "./test_output")
        
        if images:
            print(f"✅ Test successful! Generated {len(images)} images:")
            for img in images:
                print(f"   📁 {img}")
        else:
            print("❌ Test failed")
    
    else:
        json_file = sys.argv[1]
        if not os.path.exists(json_file):
            print(f"❌ File not found: {json_file}")
            return
        
        print(f"🎨 Generating image from vPrompt JSON: {json_file}")
        images = generate_from_vprompt_json(json_file)
        
        if images:
            print(f"✅ Generation successful! Created {len(images)} images:")
            for img in images:
                print(f"   📁 {img}")
        else:
            print("❌ Generation failed")

if __name__ == "__main__":
    main()
