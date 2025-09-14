#!/usr/bin/env python3
"""
IndexTTS Audio Upload Script

This script allows you to upload audio files to the IndexTTS server for voice synthesis.
Supports both FastAPI and Gradio endpoints with automatic server detection.

Usage:
    python upload_to_indextts.py --text "Hello world" --audio path/to/audio.wav
    python upload_to_indextts.py --text "你好世界" --audio Female_Chinese.wav --speed 1.2
"""

import argparse
import requests
import os
import sys
import json
from pathlib import Path

# Server configuration
INDEXTTS_SERVERS = [
    {"url": "http://192.168.68.30:8000", "name": "remote_api", "type": "fastapi"},
    {"url": "http://192.168.68.30:7860", "name": "remote_gradio", "type": "gradio"}
]

def get_available_server():
    """Find the first available IndexTTS server"""
    for server in INDEXTTS_SERVERS:
        try:
            # Use different health check endpoints for different server types
            if server['type'] == 'fastapi':
                health_endpoint = f"{server['url']}/health"
            else:
                health_endpoint = f"{server['url']}/config"
            
            response = requests.get(health_endpoint, timeout=5)
            if response.status_code == 200:
                print(f"✅ Found available server: {server['name']} at {server['url']}")
                return server
        except Exception as e:
            print(f"❌ Server {server['name']} at {server['url']} is not available: {e}")
            continue
    return None

def upload_to_fastapi(server_url, text, audio_path, **kwargs):
    """Upload to FastAPI IndexTTS server"""
    try:
        # Prepare files and data
        with open(audio_path, 'rb') as audio_file:
            files = {'reference_audio': audio_file}
            
            data = {
                'text': text,
                'speed': kwargs.get('speed', 1.0),
                'temperature': kwargs.get('temperature', 0.7),
                'top_k': kwargs.get('top_k', 20),
                'top_p': kwargs.get('top_p', 0.8),
                'repetition_penalty': kwargs.get('repetition_penalty', 1.1)
            }
            
            print(f"🚀 Sending request to FastAPI server...")
            print(f"📝 Text: {text}")
            print(f"🎵 Audio: {audio_path}")
            print(f"⚙️ Parameters: {data}")
            
            response = requests.post(
                f"{server_url}/generate", 
                files=files, 
                data=data, 
                timeout=120
            )
            
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Generation successful!")
            print(f"📊 Result: {json.dumps(result, indent=2)}")
            
            # Download the generated audio if URL is provided
            if 'audio_url' in result:
                audio_url = result['audio_url']
                if audio_url.startswith('http'):
                    download_audio(audio_url, 'generated_audio.wav')
                else:
                    print(f"🔗 Audio URL: {audio_url}")
            
            return result
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"📄 Response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("⏰ Request timeout - the server may be processing a large request")
        return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def upload_to_gradio(server_url, text, audio_path, **kwargs):
    """Upload to Gradio IndexTTS server (using gradio_client)"""
    try:
        from gradio_client import Client
        
        print(f"🚀 Connecting to Gradio server...")
        client = Client(server_url)
        
        # Prepare parameters for Gradio API
        params = [
            None,  # Form component
            text,  # Text input
            audio_path,  # Reference audio
            kwargs.get('emotion_description', ''),  # Emotion description
            kwargs.get('angry', 0.0),
            kwargs.get('sad', 0.0),
            kwargs.get('afraid', 0.0),
            kwargs.get('melancholic', 0.0),
            kwargs.get('surprised', 0.0),
            kwargs.get('calm', 0.5),
            kwargs.get('temperature', 0.7),
            kwargs.get('top_k', 50),
            kwargs.get('top_p', 0.8),
            kwargs.get('length_penalty', 1.0),
            kwargs.get('num_beams', 1),
            kwargs.get('repetition_penalty', 10.0),
            kwargs.get('max_mel_tokens', 1500),
            None, None, None, None, None, None, None, None  # Additional parameters
        ]
        
        print(f"📝 Text: {text}")
        print(f"🎵 Audio: {audio_path}")
        print(f"🚀 Sending request to Gradio server...")
        
        result = client.predict(*params, api_name="/gen_single")
        
        print(f"✅ Generation successful!")
        print(f"📊 Result: {result}")
        
        return result
        
    except ImportError:
        print("❌ gradio_client not installed. Install with: pip install gradio_client")
        return None
    except Exception as e:
        print(f"❌ Gradio request failed: {str(e)}")
        return None

def download_audio(url, filename):
    """Download audio file from URL"""
    try:
        print(f"📥 Downloading audio from {url}...")
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✅ Audio saved as {filename}")
        else:
            print(f"❌ Failed to download audio: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Download error: {str(e)}")

def resolve_audio_path(audio_path):
    """Resolve audio file path, check local VoiceSample directory if not found"""
    # Check if file exists as provided
    if os.path.exists(audio_path):
        return audio_path
    
    # Check in VoiceSample directory
    voice_sample_path = os.path.join('./api/VoiceSample', audio_path)
    if os.path.exists(voice_sample_path):
        return voice_sample_path
    
    # Check in current directory
    current_dir_path = os.path.join('.', audio_path)
    if os.path.exists(current_dir_path):
        return current_dir_path
    
    return None

def main():
    parser = argparse.ArgumentParser(description='Upload audio to IndexTTS server for voice synthesis')
    parser.add_argument('--text', '-t', required=True, help='Text to synthesize')
    parser.add_argument('--audio', '-a', required=True, help='Reference audio file path')
    parser.add_argument('--speed', type=float, default=1.0, help='Speech speed (default: 1.0)')
    parser.add_argument('--temperature', type=float, default=0.7, help='Temperature (default: 0.7)')
    parser.add_argument('--top-k', type=int, default=20, help='Top-k sampling (default: 20)')
    parser.add_argument('--top-p', type=float, default=0.8, help='Top-p sampling (default: 0.8)')
    parser.add_argument('--repetition-penalty', type=float, default=1.1, help='Repetition penalty (default: 1.1)')
    parser.add_argument('--output', '-o', help='Output filename for generated audio')
    parser.add_argument('--server', choices=['fastapi', 'gradio', 'auto'], default='auto', 
                       help='Server type to use (default: auto)')
    
    args = parser.parse_args()
    
    # Resolve audio file path
    audio_path = resolve_audio_path(args.audio)
    if not audio_path:
        print(f"❌ Audio file not found: {args.audio}")
        print("💡 Available voice samples:")
        voice_sample_dir = './api/VoiceSample'
        if os.path.exists(voice_sample_dir):
            for file in os.listdir(voice_sample_dir):
                if file.endswith(('.wav', '.mp3', '.flac')):
                    print(f"   - {file}")
        sys.exit(1)
    
    print(f"🎯 Using audio file: {audio_path}")
    
    # Find available server
    if args.server == 'auto':
        server = get_available_server()
        if not server:
            print("❌ No IndexTTS servers are available")
            sys.exit(1)
    else:
        # Find specific server type
        server = None
        for s in INDEXTTS_SERVERS:
            if s['type'] == args.server:
                server = s
                break
        if not server:
            print(f"❌ No {args.server} server configured")
            sys.exit(1)
    
    # Prepare parameters
    params = {
        'speed': args.speed,
        'temperature': args.temperature,
        'top_k': args.top_k,
        'top_p': args.top_p,
        'repetition_penalty': args.repetition_penalty
    }
    
    # Upload to server
    if server['type'] == 'fastapi':
        result = upload_to_fastapi(server['url'], args.text, audio_path, **params)
    else:
        result = upload_to_gradio(server['url'], args.text, audio_path, **params)
    
    if result:
        print(f"🎉 Voice synthesis completed successfully!")
        if args.output and 'audio_url' in result:
            download_audio(result['audio_url'], args.output)
    else:
        print(f"❌ Voice synthesis failed")
        sys.exit(1)

if __name__ == '__main__':
    main()