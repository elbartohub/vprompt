#!/usr/bin/env python3
"""
Qwen Model Installation Guide
Helps download and install the required Qwen models for image generation
"""

import os
import requests
from urllib.parse import urlparse
from pathlib import Path

def download_file(url, local_path, chunk_size=8192):
    """Download a file with progress indication"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\r  Progress: {progress:.1f}% ({downloaded:,}/{total_size:,} bytes)", end="")
        
        print(f"\n  ✅ Downloaded: {local_path}")
        return True
        
    except Exception as e:
        print(f"\n  ❌ Download failed: {e}")
        return False

def get_comfyui_models_path():
    """Try to find ComfyUI models directory"""
    # Common ComfyUI installation paths
    possible_paths = [
        "/ComfyUI/models",
        "./ComfyUI/models", 
        "../ComfyUI/models",
        "~/ComfyUI/models",
        "/opt/ComfyUI/models",
        "/usr/local/ComfyUI/models",
        # Windows paths
        "C:/ComfyUI/models",
        "C:/Users/*/ComfyUI/models"
    ]
    
    for path in possible_paths:
        expanded_path = os.path.expanduser(path)
        if os.path.exists(expanded_path):
            return expanded_path
    
    return None

def install_qwen_models():
    """Install required Qwen models for image generation"""
    print("🎨 QWEN MODEL INSTALLATION GUIDE")
    print("=" * 40)
    
    # Required Qwen models
    qwen_models = {
        'unet': {
            'filename': 'qwen_image_fp8_e4m3fn.safetensors',
            'description': 'Qwen Image UNET Model (FP8)',
            'size': '~2.5GB',
            'huggingface_url': 'https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/resolve/main/qwen_image_fp8_e4m3fn.safetensors'
        },
        'clip': {
            'filename': 'qwen_2.5_vl_7b_fp8_scaled.safetensors', 
            'description': 'Qwen 2.5 VL CLIP Model (FP8)',
            'size': '~4GB',
            'huggingface_url': 'https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/resolve/main/qwen_2.5_vl_7b_fp8_scaled.safetensors'
        },
        'vae': {
            'filename': 'qwen_image_vae.safetensors',
            'description': 'Qwen Image VAE Model',
            'size': '~200MB',
            'huggingface_url': 'https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/resolve/main/qwen_image_vae.safetensors'
        }
    }
    
    # Try to find ComfyUI models directory
    models_path = get_comfyui_models_path()
    
    if not models_path:
        print("❌ Could not find ComfyUI models directory automatically.")
        print("\nPlease manually specify your ComfyUI models path:")
        models_path = input("Enter ComfyUI models directory path: ").strip()
        
        if not os.path.exists(models_path):
            print(f"❌ Directory does not exist: {models_path}")
            return False
    
    print(f"📁 Using ComfyUI models directory: {models_path}\n")
    
    # Check which models are missing
    missing_models = []
    existing_models = []
    
    for model_type, model_info in qwen_models.items():
        model_path = os.path.join(models_path, model_type, model_info['filename'])
        if os.path.exists(model_path):
            existing_models.append((model_type, model_info))
            print(f"✅ {model_type.upper()}: {model_info['filename']} (already exists)")
        else:
            missing_models.append((model_type, model_info))
            print(f"❌ {model_type.upper()}: {model_info['filename']} (missing)")
    
    if not missing_models:
        print("\n🎉 All Qwen models are already installed!")
        return True
    
    print(f"\n📥 Need to download {len(missing_models)} models")
    total_size = sum(float(info['size'].replace('~', '').replace('GB', '').replace('MB', '')) 
                    for _, info in missing_models)
    print(f"📊 Estimated download size: ~{total_size:.1f}GB\n")
    
    # Ask for confirmation
    confirm = input("Do you want to download the missing models? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("❌ Download cancelled.")
        return False
    
    # Download missing models
    print("\n🚀 Starting downloads...\n")
    
    success_count = 0
    for model_type, model_info in missing_models:
        print(f"📦 Downloading {model_type.upper()}: {model_info['filename']}")
        print(f"   Size: {model_info['size']}")
        print(f"   Description: {model_info['description']}")
        
        model_dir = os.path.join(models_path, model_type)
        model_path = os.path.join(model_dir, model_info['filename'])
        
        if download_file(model_info['huggingface_url'], model_path):
            success_count += 1
        
        print()
    
    # Summary
    print("=" * 40)
    if success_count == len(missing_models):
        print("🎉 All Qwen models downloaded successfully!")
        print("\n📋 NEXT STEPS:")
        print("1. Restart your ComfyUI server")
        print("2. Test image generation with the Qwen workflow")
        print("3. The models should now be available in ComfyUI")
        return True
    else:
        print(f"⚠️  Downloaded {success_count}/{len(missing_models)} models")
        print("\n🔧 MANUAL INSTALLATION:")
        print("If automatic download failed, you can manually download from:")
        for model_type, model_info in missing_models:
            print(f"\n{model_type.upper()}: {model_info['filename']}")
            print(f"  URL: {model_info['huggingface_url']}")
            print(f"  Save to: {os.path.join(models_path, model_type, model_info['filename'])}")
        return False

def check_model_installation():
    """Check if Qwen models are properly installed"""
    print("\n🔍 VERIFYING MODEL INSTALLATION")
    print("-" * 35)
    
    import requests
    from dotenv import load_dotenv
    
    load_dotenv()
    
    server_address = os.getenv('COMFYUI_SERVER_ADDRESS', '127.0.0.1')
    port = os.getenv('COMFYUI_SERVER_PORT', '8188')
    base_url = f"http://{server_address}:{port}"
    
    required_models = {
        'unet': 'qwen_image_fp8_e4m3fn.safetensors',
        'clip': 'qwen_2.5_vl_7b_fp8_scaled.safetensors',
        'vae': 'qwen_image_vae.safetensors'
    }
    
    all_available = True
    
    for model_type, model_name in required_models.items():
        try:
            response = requests.get(f"{base_url}/models/{model_type}", timeout=10)
            if response.status_code == 200:
                available_models = response.json()
                if model_name in available_models:
                    print(f"✅ {model_type.upper()}: {model_name}")
                else:
                    print(f"❌ {model_type.upper()}: {model_name} not found in ComfyUI")
                    all_available = False
            else:
                print(f"⚠️  Cannot check {model_type} models (ComfyUI not responding)")
                all_available = False
        except Exception as e:
            print(f"❌ Error checking {model_type}: {e}")
            all_available = False
    
    if all_available:
        print("\n🎉 All Qwen models are available in ComfyUI!")
        print("✅ Image generation should now work with the Qwen workflow.")
    else:
        print("\n⚠️  Some models are still missing. Please:")
        print("1. Restart ComfyUI server")
        print("2. Check model file locations")
        print("3. Verify file permissions")
    
    return all_available

if __name__ == "__main__":
    try:
        success = install_qwen_models()
        if success:
            print("\n" + "=" * 40)
            input("Press Enter to verify installation...")
            check_model_installation()
    except KeyboardInterrupt:
        print("\n\n❌ Installation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")