# ComfyUI API Client

This folder contains scripts to communicate with ComfyUI API at `192.168.68.30:8188`.

## Files

- `comfyui_client.py` - Main ComfyUI API client class
- `example.py` - Example usage and test script
- `requirements.txt` - Python dependencies
- `README.md` - This file

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure ComfyUI is running at `192.168.68.30:8188`

## Usage

### Basic Example
```bash
python example.py
```

### Custom Generation
```bash
python example.py --custom
```

### Using the Client Directly
```python
from comfyui_client import generate_image

# Generate an image
images = generate_image(
    prompt_text="A beautiful sunset landscape",
    negative_prompt="blurry, low quality",
    output_dir="./my_output"
)

print(f"Generated {len(images)} images: {images}")
```

## Workflow Details

The script uses the Qwen Image generation workflow with the following components:

- **Model**: `qwen_image_fp8_e4m3fn.safetensors`
- **CLIP**: `qwen_2.5_vl_7b_fp8_scaled.safetensors`
- **VAE**: `qwen_image_vae.safetensors`
- **Resolution**: 1280x720
- **Sampler**: Euler with simple scheduler
- **Steps**: 20
- **CFG**: 2.5

## Customization

You can modify the workflow by:

1. Editing the `load_workflow()` function in `comfyui_client.py`
2. Changing generation parameters (steps, CFG, resolution, etc.)
3. Using different models or settings

## API Endpoints Used

- `POST /prompt` - Queue generation
- `GET /history/{prompt_id}` - Get execution history
- `GET /view?filename=...` - Download generated images
- `WS /ws?clientId=...` - WebSocket for real-time updates

## Error Handling

The client includes error handling for:
- Network connectivity issues
- API errors
- WebSocket connection problems
- File I/O errors

## Output

Generated images are saved to the specified output directory with ComfyUI's default naming convention.
