#!/usr/bin/env python3
"""
ComfyUI API Client
Simple script to communicate with ComfyUI API using the provided workflow
"""

import json
import requests
import websocket
import uuid
import urllib.parse
import time
import threading
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable WebSocket capture for debugging
WS_CAPTURE_ENABLED = True
WS_CAPTURE_PATH = '/Volumes/2TLexarNM610Pro/AI/vPrompt/uploads/ws_capture.log'

class ComfyUIClient:
    def __init__(self, server_address=None, port=None):
        # Use environment variables if not provided
        if server_address is None:
            server_address = os.getenv('COMFYUI_SERVER_ADDRESS', '127.0.0.1')
        if port is None:
            port = os.getenv('COMFYUI_SERVER_PORT', '8188')
            
        self.server_address = server_address
        self.port = port
        self.base_url = f"http://{server_address}:{port}"
        self.ws_url = f"ws://{server_address}:{port}/ws"

    def generate(self, prompt_json):
        """Generate an image based on the provided prompt JSON."""
        try:
            response = requests.post(f"{self.base_url}/generate", json=prompt_json)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger = logging.getLogger(__name__)
            logger.error("Error generating image: %s", e)
            return {"error": str(e)}

    def queue_prompt(self, prompt, client_id):
        """Queue a prompt for execution"""
        data = {
            "prompt": prompt,
            "client_id": client_id
        }
        
        try:
            response = requests.post(f"{self.base_url}/prompt", json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger = logging.getLogger(__name__)
            logger.error("Error queuing prompt: %s", e)
            return None
    
    def get_image(self, filename, subfolder="", folder_type="output"):
        """Get generated image from ComfyUI"""
        try:
            url_values = urllib.parse.urlencode({
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type
            })
            response = requests.get(f"{self.base_url}/view?{url_values}")
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            logger = logging.getLogger(__name__)
            logger.error("Error getting image: %s", e)
            return None
    
    def get_history(self, prompt_id):
        """Get execution history for a prompt"""
        try:
            response = requests.get(f"{self.base_url}/history/{prompt_id}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger = logging.getLogger(__name__)
            logger.error("Error getting history: %s", e)
            return None
    
    def wait_for_completion(self, prompt_id, timeout=300, progress_callback=None):
        """Wait for prompt completion via WebSocket with timeout.

        Returns True if completion event detected, False on timeout or error.
        """
        logger = logging.getLogger(__name__)
        client_id = str(uuid.uuid4())
        completion_event = threading.Event()

        # Nested WS handlers
        completion_timeout_set = False
        
        def on_message(ws, message):
            nonlocal completion_timeout_set
            logger.debug("WebSocket message: %s", message)
            # Optionally write raw WS messages to a capture file for debugging
            try:
                if WS_CAPTURE_ENABLED and WS_CAPTURE_PATH:
                    with open(WS_CAPTURE_PATH, 'a', encoding='utf-8') as fh:
                        fh.write(message + "\n")
            except Exception:
                logger.debug("Failed to write WS capture file")
            try:
                data = json.loads(message)
            except Exception as e:
                logger.debug("Failed to parse WS message: %s", e)
                return

            event_type = data.get('type', '')
            event_data = data.get('data', {}) or {}
            logger.debug("WebSocket event type: %s, keys: %s", event_type, list(event_data.keys()))
            
            # Log all event types for debugging
            if event_type not in ('crystools.monitor', 'status'):
                logger.info("Received WebSocket event: %s", event_type)

            # Try to detect completion using multiple possible event names/structures
            try:
                def _extract_progress(ed):
                    try:
                        # Ignore monitoring/telemetry blobs which are noisy
                        if isinstance(ed, dict) and ed.get('type') and 'monitor' in str(ed.get('type')):
                            return None

                        # Filter out telemetry messages
                        if event_type == "crystools.monitor":
                            return None

                        # Handle status messages with queue_remaining
                        if event_type == "status" and "queue_remaining" in ed.get("status", {}):
                            remaining = ed["status"]["queue_remaining"]
                            return max(0, 100 - remaining * 10)  # Example scaling logic

                        if isinstance(ed, dict):
                            # direct numeric fields
                            if 'progress' in ed and isinstance(ed['progress'], (int, float)):
                                return int(ed['progress'])
                            if 'percent' in ed and isinstance(ed['percent'], (int, float)):
                                return int(ed['percent'])

                            # value/max style used in progress_state
                            if 'value' in ed and 'max' in ed and ed.get('max'):
                                try:
                                    return int(round((ed.get('value', 0) / float(ed.get('max', 1))) * 100))
                                except Exception:
                                    pass

                            # nodes map: average progress across nodes if available
                            if 'nodes' in ed and isinstance(ed['nodes'], dict):
                                try:
                                    total_pct = 0.0
                                    count = 0
                                    for n in ed['nodes'].values():
                                        if isinstance(n, dict) and 'value' in n and 'max' in n and n.get('max'):
                                            total_pct += (float(n.get('value', 0)) / float(n.get('max', 1))) * 100.0
                                            count += 1
                                    if count:
                                        return int(round(total_pct / count))
                                except Exception:
                                    pass

                            # step/steps -> percent
                            if 'step' in ed and 'steps' in ed and ed['steps']:
                                try:
                                    return int(round((ed.get('step', 0) / float(ed.get('steps', 1))) * 100))
                                except Exception:
                                    pass
                            # samples_done / total_samples
                            if 'samples_done' in ed and 'total_samples' in ed and ed['total_samples']:
                                try:
                                    return int(round((ed.get('samples_done', 0) / float(ed.get('total_samples', 1))) * 100))
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    return None

                prog = _extract_progress(event_data)
                if prog is None and isinstance(event_data, dict):
                    for v in event_data.values():
                        prog = _extract_progress(v)
                        if prog is not None:
                            break

                if prog is not None:
                    logger.debug("Progress: %d%%", prog)
                    # Call progress callback if provided
                    if progress_callback:
                        try:
                            progress_callback(prog)
                        except Exception as e:
                            logger.debug("Progress callback error: %s", e)

                if event_type in ('execution_finished', 'execution_complete', 'execution_end', 'executed', 'execution_success', 'success', 'finished'):
                    if not event_data or event_data.get('prompt_id') == prompt_id:
                        logger.debug("Execution completed (finish event: %s)", event_type)
                        completion_event.set()
                        try:
                            ws.close()
                        except Exception:
                            pass
                        return

                if event_type == 'executing':
                    node = event_data.get('node')
                    pid = event_data.get('prompt_id')
                    if node is None and pid == prompt_id:
                        logger.debug("Execution completed! (executing event)")
                        completion_event.set()
                        try:
                            ws.close()
                        except Exception:
                            pass
                        return

                # Additional completion detection for ComfyUI
                if event_type == 'progress' and isinstance(event_data, dict):
                    # Check if all nodes are complete
                    if 'nodes' in event_data and isinstance(event_data['nodes'], dict):
                        all_complete = True
                        for node_data in event_data['nodes'].values():
                            if isinstance(node_data, dict) and 'value' in node_data and 'max' in node_data:
                                if node_data.get('value', 0) < node_data.get('max', 1):
                                    all_complete = False
                                    break
                        if all_complete:
                            logger.debug("All nodes complete, assuming execution finished")
                            completion_event.set()
                            try:
                                ws.close()
                            except Exception:
                                pass
                            return

            except Exception as e:
                logger.exception("Error while handling WS event: %s", e)

        def on_error(ws, error):
            logger.error("WebSocket error: %s", error)

        def on_close(ws, close_status_code, close_msg):
            logger.debug("WebSocket connection closed: %s %s", close_status_code, close_msg)

        def on_open(ws):
            logger.debug("WebSocket connection opened")

        ws = websocket.WebSocketApp(
            f"{self.ws_url}?clientId={client_id}",
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )

        # Run websocket in background thread and wait for completion_event with timeout
        ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
        ws_thread.start()

        finished = completion_event.wait(timeout)
        if not finished:
            logger.warning("WebSocket wait timed out after %s seconds", timeout)
            try:
                ws.close()
            except Exception:
                pass
            return False

        return True

def load_workflow(file_path=None):
    """Load the workflow JSON"""
    if file_path is None:
        # Load from qwen_image.json (Qwen models)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        qwen_workflow_path = os.path.join(script_dir, 'qwen_image.json')
        if os.path.exists(qwen_workflow_path):
            file_path = qwen_workflow_path
        else:
            raise FileNotFoundError("qwen_image.json workflow file not found")
    
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    else:
        raise FileNotFoundError(f"Workflow file not found: {file_path}")

def modify_prompt(workflow, new_prompt, negative_prompt="", seed=None):
    """Modify the text prompt in the workflow"""
    workflow_copy = json.loads(json.dumps(workflow))  # Deep copy

    # Update positive prompt (Qwen workflow uses node "6")
    if "6" in workflow_copy:
        workflow_copy["6"]["inputs"]["text"] = new_prompt

    # Update negative prompt (Qwen workflow uses node "7")
    if "7" in workflow_copy:
        workflow_copy["7"]["inputs"]["text"] = negative_prompt

    # Update seed if provided (KSampler uses node "3")
    if seed is not None and "3" in workflow_copy:
        workflow_copy["3"]["inputs"]["seed"] = seed

    return workflow_copy

def generate_image(prompt_text, negative_prompt="", output_dir="/Volumes/2TLexarNM610Pro/AI/vPrompt/uploads/generated", seed=None, progress_callback=None):
    """Generate an image using ComfyUI"""
    import random

    client = ComfyUIClient()

    # Load and modify workflow
    workflow = load_workflow()

    # Generate random seed if not provided
    if seed is None:
        seed = random.randint(0, 2**32 - 1)  # Random 32-bit integer
        logger = logging.getLogger(__name__)
        logger.info("Using random seed: %s", seed)

    modified_workflow = modify_prompt(workflow, prompt_text, negative_prompt, seed)

    # Generate unique client ID
    client_id = str(uuid.uuid4())

    logger = logging.getLogger(__name__)
    logger.info("Sending prompt to ComfyUI at %s", client.base_url)
    logger.debug("Prompt: %s...", prompt_text[:100])
    logger.debug("Seed: %s", seed)
    
    # Queue the prompt
    result = client.queue_prompt(modified_workflow, client_id)
    if not result:
        logger.error("Failed to queue prompt")
        return None

    prompt_id = result.get("prompt_id")
    if not prompt_id:
        logger.error("No prompt_id received")
        return None

    logger.info("Prompt queued with ID: %s", prompt_id)

    # Wait for completion (WebSocket) with timeout
    logger.info("Waiting for completion...")
    success = client.wait_for_completion(prompt_id, timeout=60, progress_callback=progress_callback)

    if not success:
        logger.warning("WebSocket did not signal completion within timeout, falling back to polling history")
        # Quick check: see if images are already available
        history = client.get_history(prompt_id)
        if history and prompt_id in history and any('images' in o for o in history[prompt_id].get('outputs', {}).values()):
            logger.info("Images already available, skipping polling")
        else:
            # Fallback: poll history for a limited time to detect completed outputs
            poll_deadline = time.time() + 15  # Reduced from 30 to 15 seconds
            while time.time() < poll_deadline:
                history = client.get_history(prompt_id)
                if history:
                    # Check if outputs exist
                    if prompt_id in history and any('images' in o for o in history[prompt_id].get('outputs', {}).values()):
                        logger.info("Found images in history via polling")
                        break
                time.sleep(1)  # Reduced from 2 to 1 second for faster polling

        if not history:
            logger.error("Failed to get history via polling")
            return None

    else:
        # Get the result
        history = client.get_history(prompt_id)
        if not history:
            logger.error("Failed to get history")
            return None
    
    # Extract output images
    images = []
    if prompt_id in history:
        for node_id, node_output in history[prompt_id]['outputs'].items():
            if 'images' in node_output:
                for image_info in node_output['images']:
                    filename = image_info['filename']
                    subfolder = image_info.get('subfolder', '')

                    # Debug: Print expected image path and check existence
                    expected_path = os.path.join(output_dir, filename)
                    logger.info("[IMAGE DEBUG] Checking for image: %s", expected_path)
                    logger.info("[IMAGE DEBUG] Exists: %s", os.path.exists(expected_path))
                    # Download image from ComfyUI server
                    image_data = client.get_image(filename, subfolder)
                    if image_data:
                        os.makedirs(output_dir, exist_ok=True)
                        if filename.startswith("ComfyUI_"):
                            new_filename = "vPrompt_" + filename[len("ComfyUI_"):]
                        else:
                            new_filename = "vPrompt_" + filename
                        local_path = os.path.join(output_dir, new_filename)
                        with open(local_path, 'wb') as f:
                            f.write(image_data)
                        images.append(local_path)
                        logger.info("Image downloaded and saved: %s", local_path)
                    else:
                        logger.error("Failed to download image data for %s", filename)

    logger.info("generate_image returning %s images", len(images))
    return images

if __name__ == "__main__":
    # Example usage
    prompt = "A beautiful sunset over a mountain landscape, cinematic lighting, highly detailed, 8k resolution"
    negative = "blurry, low quality, bad anatomy"
    
    logger = logging.getLogger(__name__)
    logger.info("ComfyUI API Client Test")
    logger.info("%s", "=" * 50)
    
    try:
        images = generate_image(prompt, negative)
        if images:
            logger.info("Successfully generated %s images:", len(images))
            for img in images:
                logger.info("  - %s", img)
        else:
            logger.info("No images generated")
    except Exception as e:
        logger.exception("Error: %s", e)
