#!/usr/bin/env python3
"""
Simple Image Generation Mock
Creates placeholder functionality for image generation when advanced image generation service is not available
"""

import os
import json
import time
from datetime import datetime

def json_to_prompt(vprompt_json):
    """Convert vPrompt JSON to a simple prompt"""
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

def generate_from_vprompt_dict(vprompt_dict, output_dir="./vprompt_output", seed=None):
    """Generate placeholder for image generation - returns mock image paths."""
    try:
        positive, negative = json_to_prompt(vprompt_dict)

        if not positive:
            print("❌ Failed to extract prompt from dictionary")
            return None

        print(f"📝 Generated prompt from vPrompt data:")
        print(f"   Positive: {positive[:100]}...")
        if seed is not None:
            print(f"   Seed: {seed}")
        else:
            print(f"   Seed: Random (not specified)")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Simulate brief processing time
        time.sleep(0.2)

        # Create a simple placeholder image info (simulate generation)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_generated.png"
        filepath = os.path.join(output_dir, filename)

        # Create a simple text file as placeholder (since we don't have image generation yet)
        with open(filepath.replace('.png', '_prompt.txt'), 'w', encoding='utf-8') as f:
            f.write(f"Generated Prompt:\n{positive}\n\nNegative Prompt:\n{negative}")

        print(f"📄 Saved prompt to: {filepath.replace('.png', '_prompt.txt')}")
        print("⚠️  Note: This is a placeholder - actual image generation requires additional setup")

        # Return placeholder image path (will result in 404 but structure is ready)
        return [filepath]

    except Exception as e:
        print(f"❌ Error processing vPrompt dictionary: {e}")
        return None

def main():
    """CLI interface for testing"""
    print("🧪 Testing vPrompt integration (mock mode)")
    
    # Test with sample vPrompt JSON
    sample_json = {
        "Scene": "A magical forest clearing at twilight",
        "ambiance_or_mood": "mystical and enchanting",
        "Location": "ancient woodland with towering trees",
        "Visual style": "fantasy art with ethereal lighting",
        "lighting": "soft moonbeams filtering through leaves",
        "extra_desc": "fireflies dancing, moss-covered stones, magical atmosphere"
    }
    
    print("🎯 Testing with sample vPrompt JSON...")
    images = generate_from_vprompt_dict(sample_json, "./test_output")
    
    if images:
        print(f"✅ Test successful! Generated {len(images)} placeholder files:")
        for img in images:
            print(f"   📁 {img}")
    else:
        print("❌ Test failed")

if __name__ == "__main__":
    main()
