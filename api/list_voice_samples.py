#!/usr/bin/env python3
"""
Script to list available voice samples through ComfyUI API
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def list_comfyui_files(server_address=None, port=None, file_type="input"):
    """
    List files available in ComfyUI server
    
    Args:
        server_address: ComfyUI server address (default from env)
        port: ComfyUI server port (default from env)
        file_type: Type of files to list (input, output, temp)
    
    Returns:
        List of available files or None if error
    """
    if server_address is None:
        server_address = os.getenv('COMFYUI_SERVER_ADDRESS', '127.0.0.1')
    if port is None:
        port = os.getenv('COMFYUI_SERVER_PORT', '8188')
        
    base_url = f"http://{server_address}:{port}"
    
    # Try different possible endpoints for listing files
    endpoints_to_try = [
        f"/view",  # Basic view endpoint
        f"/files",  # Possible files endpoint
        f"/files/{file_type}",  # Files by type
        f"/api/files",  # API files endpoint
        f"/api/files/{file_type}",  # API files by type
        f"/input",  # Direct input endpoint
        f"/models",  # Models endpoint
        f"/api/models",  # API models endpoint
    ]
    
    print(f"Checking ComfyUI server at {base_url}")
    print(f"Looking for {file_type} files...\n")
    
    for endpoint in endpoints_to_try:
        try:
            url = base_url + endpoint
            print(f"Trying: {url}")
            response = requests.get(url, timeout=10)
            
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    # Try to parse as JSON
                    data = response.json()
                    print(f"  Response (JSON): {json.dumps(data, indent=2)[:500]}...")
                    return data
                except json.JSONDecodeError:
                    # Not JSON, maybe HTML or plain text
                    content = response.text[:500]
                    print(f"  Response (Text): {content}...")
                    
            elif response.status_code == 404:
                print(f"  Not found")
            else:
                print(f"  Error: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"  Connection error: {e}")
        
        print()
    
    return None

def check_specific_audio_files(server_address=None, port=None):
    """
    Check if the specific audio reference files exist
    """
    if server_address is None:
        server_address = os.getenv('COMFYUI_SERVER_ADDRESS', '127.0.0.1')
    if port is None:
        port = os.getenv('COMFYUI_SERVER_PORT', '8188')
        
    base_url = f"http://{server_address}:{port}"
    
    # Audio files from VibeVoice_API.json
    audio_files = [
        "GoogleNewAI.wav",
        "我係由人工智能技術創建嘅.mp3"
    ]
    
    print(f"Checking specific audio reference files at {base_url}")
    print("Files from VibeVoice_API.json:\n")
    
    for filename in audio_files:
        try:
            # Try to access the file through view endpoint
            import urllib.parse
            url_values = urllib.parse.urlencode({
                "filename": filename,
                "subfolder": "",
                "type": "input"
            })
            url = f"{base_url}/view?{url_values}"
            
            print(f"Checking: {filename}")
            print(f"  URL: {url}")
            
            response = requests.head(url, timeout=10)  # Use HEAD to avoid downloading
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  ✅ File exists and accessible")
                if 'content-length' in response.headers:
                    size = int(response.headers['content-length'])
                    print(f"  Size: {size} bytes ({size/1024:.1f} KB)")
            elif response.status_code == 404:
                print(f"  ❌ File not found")
            else:
                print(f"  ⚠️  Unexpected status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Connection error: {e}")
        
        print()

if __name__ == "__main__":
    print("ComfyUI Voice Samples Checker")
    print("=" * 50)
    
    # First, try to list all available files
    print("\n1. Attempting to list all available files...")
    files = list_comfyui_files(file_type="input")
    
    print("\n" + "="*50)
    
    # Then check specific audio reference files
    print("\n2. Checking specific audio reference files...")
    check_specific_audio_files()
    
    print("\n" + "="*50)
    print("\nDone! If files are not accessible, they may need to be placed in:")
    print("- ComfyUI/input/ directory")
    print("- ComfyUI/models/audio/ directory")
    print("- Or the appropriate ComfyUI input folder")