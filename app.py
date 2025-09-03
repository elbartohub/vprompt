import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, send_from_directory
from werkzeug.utils import secure_filename
# 假設 Gemini API 有官方 Python SDK
# from gemini_flash_lite_sdk import GeminiClient
import requests
from dotenv import load_dotenv
import base64
from flask import make_response
import threading
import uuid
import time

# Add the `api` directory to the Python path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))
from comfyui_client import ComfyUIClient  # Import ComfyUIClient from the `api` directory

# In-memory job store for generation progress tracking
generation_jobs = {}
generation_jobs_lock = threading.Lock()

# Import image generation integration
try:
    from api.vprompt_integration import generate_from_vprompt_dict
    COMFYUI_AVAILABLE = True
    print("[DEBUG] Image generation integration available")
except ImportError as e:
    try:
        from api.simple_integration import generate_from_vprompt_dict
        COMFYUI_AVAILABLE = True
        print("[DEBUG] Using simple integration (mock mode)")
    except ImportError as e2:
        COMFYUI_AVAILABLE = False
        print(f"[DEBUG] No image integration available: {e2}")

UPLOAD_FOLDER = 'uploads'
GENERATED_FOLDER = os.path.abspath('uploads/generated')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'heic', 'heif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)

# --- WS capture control (for capturing raw ComfyUI websocket messages) ---
@app.route('/capture_ws_start', methods=['POST'])
def capture_ws_start():
    """Enable websocket message capture to a named file.

    POST form params:
      - filename: optional filename under GENERATED_FOLDER to write capture
    """
    filename = request.form.get('filename') or f"ws_capture_{int(time.time())}.log"
    path = os.path.join(GENERATED_FOLDER, secure_filename(filename))
    # Ensure file exists and is empty
    open(path, 'w', encoding='utf-8').close()
    try:
        # Set globals in comfyui_client module
        import importlib
        cc = importlib.import_module('api.comfyui_client')
        setattr(cc, 'WS_CAPTURE_ENABLED', True)
        setattr(cc, 'WS_CAPTURE_PATH', path)
        return jsonify({'capture_path': path}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/capture_ws_stop', methods=['POST'])
def capture_ws_stop():
    """Disable websocket capture and return the capture file path if present."""
    try:
        import importlib
        cc = importlib.import_module('api.comfyui_client')
        path = getattr(cc, 'WS_CAPTURE_PATH', None)
        setattr(cc, 'WS_CAPTURE_ENABLED', False)
        setattr(cc, 'WS_CAPTURE_PATH', None)
        return jsonify({'capture_path': path}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/capture_ws_download')
def capture_ws_download():
    """Download the most recently written WS capture file if available."""
    try:
        import importlib
        cc = importlib.import_module('api.comfyui_client')
        path = getattr(cc, 'WS_CAPTURE_PATH', None)
        # If path is None (capture stopped), look for last file in GENERATED_FOLDER
        if not path:
            files = [os.path.join(GENERATED_FOLDER, f) for f in os.listdir(GENERATED_FOLDER) if f.startswith('ws_capture_')]
            if not files:
                return jsonify({'error': 'No capture file found'}), 404
            path = sorted(files, key=os.path.getmtime)[-1]
        if not path or not os.path.exists(path):
            return jsonify({'error': 'Capture file not found'}), 404
        return send_file(path, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


load_dotenv()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_image_mime_type(filename):
    """Get the appropriate MIME type for the image file"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    mime_types = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'heic': 'image/heic',
        'heif': 'image/heif'
    }
    return mime_types.get(ext, 'image/jpeg')  # Default to JPEG for unknown types

def get_default_camera_motion(prompt_type, scene, character):
    """Generate default camera motion based on scene and character context"""
    if prompt_type != 'video':
        return ''
    
    # Camera motion suggestions based on scene context
    scene_motions = {
        '戶外': ['sweeping drone shot', 'tracking shot through landscape', 'wide establishing shot'],
        '室內': ['intimate handheld movement', 'smooth dolly shot', 'close-up push-in'],
        '森林': ['tracking through trees', 'low-angle forest walk', 'canopy reveal shot'],
        '海邊': ['aerial coastal flyover', 'wave-following tracking', 'sunset crane shot'],
        '咖啡廳': ['subtle handheld intimacy', 'table-level dolly', 'window reflection shot'],
        '辦公室': ['corporate tracking shot', 'meeting room push-in', 'window city view'],
    }
    
    # Character-based motion suggestions
    character_motions = {
        '情侶': 'romantic close-up orbit',
        '攝影師': 'dynamic following shot',
        '學生': 'youthful tracking movement',
        '商人': 'confident dolly approach',
        '藝術家': 'creative rotating shot',
        '男': 'steady character tracking',
        '女': 'elegant following movement',
        '男孩': 'playful handheld motion',
        '女孩': 'gentle floating movement',
        '老人': 'respectful slow push-in',
    }
    
    # Try to match scene first, then character
    if scene and scene in scene_motions:
        return scene_motions[scene][0]  # Return first suggestion
    elif character and character in character_motions:
        return character_motions[character]
    else:
        # Default cinematic motions
        return 'smooth tracking shot'

def get_client_ip():
    """Get the client's IP address from request headers"""
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()

def get_location_from_ip(ip_address):
    """Get location information from IP address using a free API"""
    try:
        # Use a simple free IP geolocation service
        response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                return {
                    'country': data.get('country', 'Unknown'),
                    'region': data.get('regionName', 'Unknown'),
                    'city': data.get('city', 'Unknown'),
                    'timezone': data.get('timezone', 'Unknown'),
                    'isp': data.get('isp', 'Unknown')
                }
    except Exception as e:
        print(f"[DEBUG] Error getting location for IP {ip_address}: {str(e)}")
    
    return {
        'country': 'Unknown',
        'region': 'Unknown', 
        'city': 'Unknown',
        'timezone': 'Unknown',
        'isp': 'Unknown'
    }

def log_user_interaction(user_inputs, prompt_result, prompt_json_result, uploaded_file_path=None, generated_images=None):
    """Log user interaction to JSON file"""
    print(f"[DEBUG] log_user_interaction called with result length: {len(prompt_result) if prompt_result else 0}")
    try:
        # Create logs directory if it doesn't exist
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        
        # Get client information
        client_ip = get_client_ip()
        location_info = get_location_from_ip(client_ip)
        
        # Create log entry
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'client_ip': client_ip,
            'location': location_info,
            'user_inputs': user_inputs,
            'prompt_result': prompt_result,
            'prompt_json_result': prompt_json_result,
            'uploaded_file_path': uploaded_file_path,
            'generated_images': generated_images,
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        }
        
        # Generate log filename with date
        log_filename = f"user_interactions_{datetime.now().strftime('%Y-%m-%d')}.json"
        log_filepath = os.path.join(log_dir, log_filename)
        
        # Read existing logs or create new list
        if os.path.exists(log_filepath):
            with open(log_filepath, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = []
        
        # Add new log entry
        logs.append(log_entry)
        
        # Write back to file
        with open(log_filepath, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        
        print(f"[DEBUG] Logged user interaction to {log_filepath}")
        
    except Exception as e:
        print(f"[DEBUG] Error logging user interaction: {str(e)}")

def handle_regenerate_request():
    """Handle regenerate image request from edited JSON using async job system"""
    try:
        # Get the JSON data from the form
        json_data_str = request.form.get('json_data')
        if not json_data_str:
            return jsonify({'error': 'No JSON data provided'}), 400

        # Parse the JSON
        try:
            prompt_json = json.loads(json_data_str)
            # Sanitize extra_desc if present
            if 'extra_desc' in prompt_json and isinstance(prompt_json['extra_desc'], str):
                # Replace multiple \r\n or \n with a single newline
                import re
                prompt_json['extra_desc'] = re.sub(r'(\r\n|\n){2,}', '\n', prompt_json['extra_desc'])
        except json.JSONDecodeError as e:
            return jsonify({'error': f'Invalid JSON format: {str(e)}'}), 400

        # Get optional seed parameter
        seed = None
        seed_str = request.form.get('seed')
        if seed_str:
            try:
                seed = int(seed_str)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid seed value'}), 400

        print(f"[DEBUG] Regenerating image from edited JSON: {prompt_json}")
        if seed is not None:
            print(f"[DEBUG] Using seed: {seed}")
        # Debug: echo back received JSON in response for frontend confirmation
        debug_echo = json.dumps(prompt_json, ensure_ascii=False, indent=2)

        # Generate a unique job ID for the regenerate request
        job_id = str(uuid.uuid4())

        # Initialize the job in the global jobs dictionary
        with generation_jobs_lock:
            generation_jobs[job_id] = {
                'status': 'pending',
                'progress': 0,
                'images': [],
                'error': None,
                'seed': seed
            }

        # Start background generation thread
        thread = threading.Thread(target=_background_generate, args=(job_id, prompt_json, seed))
        thread.daemon = True
        thread.start()

        # Return job ID for frontend to poll
        return jsonify({
            'job_id': job_id,
            'message': 'Image regeneration started',
            'seed': seed,
            'debug_echo': debug_echo
        }), 200

    except Exception as e:
        print(f"[DEBUG] Error in handle_regenerate_request: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/', methods=['GET', 'POST'])
def index():
    # Initialize variables
    prompt_text = ''
    prompt_json = None
    prompt_json_str = ''
    image_url = None
    image_path = None
    file = None
    generated_images = None
    
    print("[DEBUG] Request method:", request.method)
    
    # Read cookie defaults
    prompt_type = request.cookies.get('prompt_type', 'image')
    output_lang = request.cookies.get('output_lang', 'en')
    # Handle zh-TW to zh-tw conversion for display consistency
    output_lang_display = 'zh-tw' if output_lang == 'zh-TW' else output_lang
    time = request.cookies.get('time', '16:00')
    scene = request.cookies.get('scene')
    if scene is None or scene == '':
        scene = '其它'
    custom_scene = request.cookies.get('custom_scene', '')
    character = request.cookies.get('character')
    if character is None or character == '':
        character = '其它'
    custom_character = request.cookies.get('custom_character', '')
    extra_desc = request.cookies.get('extra_desc', '')
    creative_mode = request.cookies.get('creative_mode', 'false') == 'true'
    include_ending = request.cookies.get('include_ending', 'false') == 'true'
    multiple_scenes = request.cookies.get('multiple_scenes', 'false') == 'true'
    image_filename = request.cookies.get('image_filename', '')
    bypass_time = request.cookies.get('bypass_time', 'true') == 'true'
    
    if image_filename:
        # Check if the file is HEIC/HEIF and use conversion endpoint for display
        if image_filename.lower().endswith(('.heic', '.heif')):
            image_url = url_for('convert_heic', filename=image_filename)
        else:
            image_url = url_for('uploaded_file', filename=image_filename)
    else:
        image_url = None
    
    if request.method == 'POST':
        # Check if this is a regenerate action
        action = request.form.get('action')
        if action == 'regenerate':
            return handle_regenerate_request()
        
        prompt_type = request.form.get('prompt_type')
        output_lang = request.form.get('output_lang', 'en')
        print(f"[DEBUG] Form data: prompt_type={prompt_type}, output_lang={output_lang}")
        # Store the original form value for display, but use converted value for API calls
        output_lang_display = output_lang
        # 修正 zh-tw 映射
        if output_lang == 'zh-tw':
            output_lang = 'zh-TW'
        bypass_time = request.form.get('bypass_time', 'true') == 'true'
        time = request.form.get('time') if not bypass_time else None
        scene = request.form.get('scene')
        custom_scene = request.form.get('custom_scene')
        character = request.form.get('character')
        custom_character = request.form.get('custom_character')
        extra_desc = request.form.get('extra_desc')
        creative_mode = request.form.get('creative_mode') == 'true'
        include_ending = request.form.get('include_ending') == 'true'
        multiple_scenes = request.form.get('multiple_scenes') == 'true'
        file = request.files.get('image')
        image_path = None
        image_filename = ''

        # Set cookies for extra_desc and bypass_time
        resp = None
        def set_cookie_response(html):
            nonlocal resp
            resp = make_response(html)
            resp.set_cookie('extra_desc', extra_desc or '', max_age=60*60*24*30)
            resp.set_cookie('bypass_time', str(bypass_time).lower(), max_age=60*60*24*30)
            return resp
        
        print(f"[DEBUG] Form data: time={time}, bypass_time={bypass_time}, scene={scene}, custom_scene={custom_scene}, character={character}, custom_character={custom_character}, extra_desc={extra_desc}, creative_mode={creative_mode}, include_ending={include_ending}, multiple_scenes={multiple_scenes}, file={file.filename if file else None}")
        
        # 若所有欄位皆空，直接清空結果
        if not any([prompt_type, output_lang, scene, custom_scene, character, custom_character, extra_desc, file]):
            print("[DEBUG] All fields empty, clearing result.")
            prompt_json = None
            prompt_text = ''
            image_url = None
        else:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(image_path)
                # Check if the file is HEIC/HEIF and use conversion endpoint for display
                if filename.lower().endswith(('.heic', '.heif')):
                    image_url = url_for('convert_heic', filename=filename)
                else:
                    image_url = url_for('uploaded_file', filename=filename)
                image_filename = filename
                print(f"[DEBUG] Image saved: {image_path}")
        # 圖片識別（Gemini 2.0 Flash HTTP API）
        if image_path:
            api_key = os.getenv('GEMINI_API_KEY', 'YOUR_API_KEY')
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            
            # Get appropriate MIME type for the uploaded file
            mime_type = get_image_mime_type(filename)
            # 根據 output_lang 設定 prompt 語言
            lang_map = {
                'en': 'English',
                'zh-TW': 'Traditional Chinese',
                'zh-CN': 'Simplified Chinese',
                'ja': 'Japanese',
                'ko': 'Korean',
                'fr': 'French',
                'de': 'German',
                'es': 'Spanish'
            }
            prompt_lang = lang_map.get(output_lang, 'English')
            if prompt_type == 'video':
                if creative_mode:
                    prompt_text_recog = f"請詳細識別這張圖片，並以 json 格式輸出影片內容：Scene、ambiance_or_mood、Location、Visual style、camera motion、lighting{'、ending' if include_ending else ''}。創意模式：請極具創意、藝術性和實驗性。對於 'camera motion'，請建議大膽、創新且具電影感的攝影機運動，突破創意界限（例如：'圍繞主體的超現實螺旋下降'、'穿越飄渺空間的時間延遲追蹤'、'反重力軌道鏡頭'、'夢幻般的變形視角'、'萬花筒式旋轉序列'、'詩意流動轉場'）。讓畫面視覺震撼且情感強烈。所有回應內容一律使用{prompt_lang}。"
                else:
                    prompt_text_recog = f"請詳細識別這張圖片，並以 json 格式輸出影片內容：Scene、ambiance_or_mood、Location、Visual style、camera motion、lighting{'、ending' if include_ending else ''}。對於 'camera motion'，請根據場景建議富有創意和電影感的攝影機運動（例如：追蹤鏡頭、升降運動、手持親密感、空拍鏡頭、推拉鏡頭、移動推軌、旋轉等）。所有回應內容一律使用{prompt_lang}。"
            else:
                if creative_mode:
                    prompt_text_recog = f"請詳細識別這張圖片，並以 json 格式輸出：Scene、ambiance_or_mood、Location、Visual style、lighting{'、ending' if include_ending else ''}。創意模式：請極具藝術性、實驗性和想像力。以大膽的視覺概念、非傳統的視角和創新的故事敘述方式突破創意界限。所有回應內容一律使用{prompt_lang}。"
                else:
                    prompt_text_recog = f"請詳細識別這張圖片，並以 json 格式輸出：Scene、ambiance_or_mood、Location、Visual style、lighting{'、ending' if include_ending else ''}。所有回應內容一律使用{prompt_lang}。"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt_text_recog},
                            {"inline_data": {"mime_type": mime_type, "data": img_b64}}
                        ]
                    }
                ]
            }
            headers = {
                "Content-Type": "application/json",
                "X-goog-api-key": api_key
            }
            print(f"[DEBUG] Gemini API payload: {payload}")
            resp = requests.post(url, json=payload, headers=headers)
            print(f"[DEBUG] Gemini API status: {resp.status_code}")
            import re, json as pyjson
            try:
                resp_json = resp.json()
                print(f"[DEBUG] Gemini API response: {resp_json}")
                text = resp_json['candidates'][0]['content']['parts'][0]['text']
            except Exception as e:
                print(f"[DEBUG] Gemini API parse error: {e}")
                text = ''
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    parsed_result = pyjson.loads(match.group())
                    print(f"[DEBUG] Parsed image recognition result: {parsed_result}")
                    # Extract the content from nested structure if present
                    if 'VIDEO' in parsed_result:
                        result = parsed_result['VIDEO']
                    elif 'IMAGE' in parsed_result:
                        result = parsed_result['IMAGE']
                    else:
                        result = parsed_result
                except Exception as e:
                    print(f"[DEBUG] JSON parse error: {e}")
                    result = None
            else:
                print("[DEBUG] No JSON found in Gemini response text.")
                result = None
            # 若 result 為 None，則用空欄位
            if not result:
                print("[DEBUG] Using empty fields for image recognition result.")
                if prompt_type == 'video':
                    result = {'Scene': '', 'ambiance_or_mood': '', 'Location': '', 'Visual style': '', 'camera motion': '', 'lighting': '', 'ending': ''}
                else:
                    result = {'Scene': '', 'ambiance_or_mood': '', 'Location': '', 'Visual style': '', 'lighting': '', 'ending': ''}
        else:
            print("[DEBUG] No image uploaded, using user input for result.")
            # Create a more intelligent user input result
            user_scene = scene if scene != '其它' else custom_scene
            user_character = character if character != '其它' else custom_character
            
            # Build result based on available user inputs
            result = {
                'Scene': user_scene if user_scene and user_scene != '其它' else '',
                'ambiance_or_mood': '',  # Will be inferred by Gemini based on other inputs
                'Location': user_scene if user_scene and user_scene != '其它' else '',  # Use scene as location if provided
                'Visual style': '',  # Will be inferred
                'camera motion': get_default_camera_motion(prompt_type, user_scene, user_character) if prompt_type == 'video' else '',
                'lighting': '',  # Will be inferred
                'ending': ''  # Will be inferred
            }
            
            # If we have meaningful user inputs, let Gemini fill in the gaps
            if any([user_scene, user_character, extra_desc, time]):
                print("[DEBUG] User provided meaningful inputs, will ask Gemini to enhance them.")
                # Create a prompt for Gemini to enhance user inputs
                user_inputs = []
                if user_scene: user_inputs.append(f"場景: {user_scene}")
                if user_character: user_inputs.append(f"主角: {user_character}")
                if time: user_inputs.append(f"時間: {time}")
                if extra_desc: user_inputs.append(f"額外描述: {extra_desc}")
                
                user_input_text = ", ".join(user_inputs)
                
                # Enhance the user inputs
                api_key = os.getenv('GEMINI_API_KEY', 'YOUR_API_KEY')
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
                
                # Language mapping for enhancement prompt
                lang_map = {
                    'en': 'English',
                    'zh-TW': 'Traditional Chinese',
                    'zh-CN': 'Simplified Chinese',
                    'ja': 'Japanese',
                    'ko': 'Korean',
                    'fr': 'French',
                    'de': 'German',
                    'es': 'Spanish'
                }
                prompt_lang = lang_map.get(output_lang, 'English')
                
                if output_lang == 'en':
                    if prompt_type == 'video':
                        if creative_mode:
                            scene_instruction = "Create MULTIPLE connected scenes in a sequence" if multiple_scenes else "Create ONE single scene only"
                            enhance_prompt = f"Based on these user inputs: {user_input_text}, please create a detailed JSON for VIDEO content with the following fields: Scene, ambiance_or_mood, Location, Visual style, camera motion, lighting{', ending' if include_ending else ''}. IMPORTANT: {scene_instruction}. For 'camera motion', choose ONLY ONE specific camera movement - do not combine multiple shots. Create ONE BOLD, IMAGINATIVE, and UNCONVENTIONAL camera movement that pushes creative boundaries (e.g., 'surreal floating through impossible geometries' OR 'time-warped spiral dance around emotions' OR 'gravity-defying liquid mercury flows' OR 'dream-logic perspective morphing' - pick just ONE). Make it visually stunning, emotionally powerful, and artistically groundbreaking. Output in {prompt_lang} and format as valid JSON only."
                        else:
                            scene_instruction = "Create MULTIPLE connected scenes in a sequence" if multiple_scenes else "Create ONE single scene only"
                            enhance_prompt = f"Based on these user inputs: {user_input_text}, please create a detailed JSON for VIDEO content with the following fields: Scene, ambiance_or_mood, Location, Visual style, camera motion, lighting{', ending' if include_ending else ''}. IMPORTANT: {scene_instruction}. For 'camera motion', choose ONLY ONE specific camera movement - do not combine multiple shots. Create ONE CREATIVE and CINEMATIC camera movement that enhances the storytelling (e.g., 'smooth tracking shot following the subject' OR 'dramatic crane shot revealing the landscape' OR 'intimate handheld close-up' OR 'sweeping drone shot' - pick just ONE). Make the camera motion specific, cinematic, and emotionally engaging. Output in {prompt_lang} and format as valid JSON only."
                    else:
                        if creative_mode:
                            scene_instruction = "Create MULTIPLE connected scenes in a sequence" if multiple_scenes else "Create ONE single scene only"
                            enhance_prompt = f"Based on these user inputs: {user_input_text}, please create a detailed JSON with the following fields: Scene, ambiance_or_mood, Location, Visual style, lighting{', ending' if include_ending else ''}. IMPORTANT: {scene_instruction}. CREATIVE MODE: Be highly artistic, experimental, and imaginative. Push creative boundaries with bold visual concepts, unconventional perspectives, surreal elements, and innovative storytelling approaches. Fill in missing fields with groundbreaking creative details. Output in {prompt_lang} and format as valid JSON only."
                        else:
                            scene_instruction = "Create MULTIPLE connected scenes in a sequence" if multiple_scenes else "Create ONE single scene only"
                            enhance_prompt = f"Based on these user inputs: {user_input_text}, please create a detailed JSON with the following fields: Scene, ambiance_or_mood, Location, Visual style, lighting{', ending' if include_ending else ''}. IMPORTANT: {scene_instruction}. Fill in creative and appropriate details for missing fields. Output in {prompt_lang} and format as valid JSON only."
                else:
                    if prompt_type == 'video':
                        if creative_mode:
                            scene_instruction = "創建多個連續場景序列" if multiple_scenes else "只創建單一場景"
                            enhance_prompt = f"根據這些用戶輸入: {user_input_text}，請創建一個專為影片內容設計的詳細 JSON，包含以下欄位：Scene、ambiance_or_mood、Location、Visual style、camera motion、lighting{'、ending' if include_ending else ''}。重要：{scene_instruction}。對於 'camera motion' 欄位，請只選擇一種特定的攝影機運動 - 不要組合多個鏡頭。創造一個大膽、富有想像力且非傳統的攝影機運動，突破創意界限（例如：'穿越不可能幾何體的超現實漂浮' 或 '圍繞情感的時間扭曲螺旋舞蹈' 或 '反重力液態水銀流動' 或 '夢境邏輯視角變形' - 只選擇其中一種）。讓它視覺震撼、情感強烈且藝術性突破。請用{prompt_lang}回應，並只輸出有效的 JSON 格式。"
                        else:
                            scene_instruction = "創建多個連續場景序列" if multiple_scenes else "只創建單一場景"
                            enhance_prompt = f"根據這些用戶輸入: {user_input_text}，請創建一個專為影片內容設計的詳細 JSON，包含以下欄位：Scene、ambiance_or_mood、Location、Visual style、camera motion、lighting{'、ending' if include_ending else ''}。重要：{scene_instruction}。對於 'camera motion' 欄位，請只選擇一種特定的攝影機運動 - 不要組合多個鏡頭。創造一個富有創意和電影感的攝影機運動，增強故事敘述效果（例如：'平滑追蹤鏡頭跟隨主體' 或 '戲劇性升降鏡頭展現風景' 或 '親密手持特寫' 或 '掃描式空拍鏡頭' - 只選擇其中一種）。讓攝影機運動具體、有電影感且富有情感張力。請用{prompt_lang}回應，並只輸出有效的 JSON 格式。"
                    else:
                        if creative_mode:
                            scene_instruction = "創建多個連續場景序列" if multiple_scenes else "只創建單一場景"
                            enhance_prompt = f"根據這些用戶輸入: {user_input_text}，請創建一個詳細的 JSON，包含以下欄位：Scene、ambiance_or_mood、Location、Visual style、lighting{'、ending' if include_ending else ''}。重要：{scene_instruction}。創意模式：請極具藝術性、實驗性和想像力。以大膽的視覺概念、非傳統的視角、超現實元素和創新的故事敘述方式突破創意界限。為缺少的欄位填入突破性的創意細節。請用{prompt_lang}回應，並只輸出有效的 JSON 格式。"
                        else:
                            scene_instruction = "創建多個連續場景序列" if multiple_scenes else "只創建單一場景"
                            enhance_prompt = f"根據這些用戶輸入: {user_input_text}，請創建一個詳細的 JSON，包含以下欄位：Scene、ambiance_or_mood、Location、Visual style、lighting{'、ending' if include_ending else ''}。重要：{scene_instruction}。為缺少的欄位填入富有創意且合適的細節。請用{prompt_lang}回應，並只輸出有效的 JSON 格式。"
                
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": enhance_prompt}
                            ]
                        }
                    ]
                }
                headers = {
                    "Content-Type": "application/json",
                    "X-goog-api-key": api_key
                }
                
                try:
                    print(f"[DEBUG] Gemini enhancement prompt: {enhance_prompt}")
                    resp = requests.post(url, json=payload, headers=headers)
                    print(f"[DEBUG] Gemini enhancement API status: {resp.status_code}")
                    
                    if resp.status_code == 200:
                        import re, json as pyjson
                        resp_json = resp.json()
                        print(f"[DEBUG] Gemini enhancement API response: {resp_json}")
                        text = resp_json['candidates'][0]['content']['parts'][0]['text']
                        
                        # Extract JSON from response
                        match = re.search(r'\{[\s\S]*\}', text)
                        if match:
                            try:
                                enhanced_result = pyjson.loads(match.group())
                                print(f"[DEBUG] Parsed enhanced result: {enhanced_result}")
                                # Extract the content from nested structure if present
                                if 'VIDEO' in enhanced_result:
                                    result = enhanced_result['VIDEO']
                                elif 'IMAGE' in enhanced_result:
                                    result = enhanced_result['IMAGE']
                                else:
                                    result = enhanced_result
                            except Exception as e:
                                print(f"[DEBUG] JSON parse error for enhancement: {e}")
                                # Keep the original result if parsing fails
                        else:
                            print("[DEBUG] No JSON found in Gemini enhancement response.")
                    else:
                        print(f"[DEBUG] Gemini enhancement API failed with status: {resp.status_code}")
                        
                except Exception as e:
                    print(f"[DEBUG] Gemini enhancement API error: {e}")
                    # Keep the original result if API call fails
        
        # 確保 result 總是有預設值，防止 KeyError
        if 'result' not in locals() or result is None:
            print("[DEBUG] No result available, using default empty fields.")
            result = {
                'Scene': '',
                'ambiance_or_mood': '',
                'Location': '',
                'Visual style': '',
                'camera motion': '',
                'lighting': '',
                'ending': ''
            }
        
        print(f"[DEBUG] Result before key checking: {result}")
        
        # 確保 result 包含所有必要的鍵
        default_keys = ['Scene', 'ambiance_or_mood', 'Location', 'Visual style', 'camera motion', 'lighting']
        if include_ending:
            default_keys.append('ending')
        for key in default_keys:
            if key not in result:
                result[key] = ''
                print(f"[DEBUG] Added missing key '{key}' to result")
        
        # 整合用戶選擇
        main_character = character if character != '其它' else custom_character
        def skip_custom(val):
            return '' if val == '用戶自定' else val
        def infer_or_value(val, field_name):
            return val if val else ''
        def safe_get(dictionary, key, default=''):
            """安全地從字典獲取值，避免 KeyError"""
            return dictionary.get(key, default) if dictionary else default
            
        prompt_json = {
            'Scene': infer_or_value(skip_custom(safe_get(result, 'Scene')), 'Scene'),
            'ambiance_or_mood': infer_or_value(skip_custom(safe_get(result, 'ambiance_or_mood')), 'ambiance_or_mood'),
            'Location': infer_or_value(skip_custom(safe_get(result, 'Location')), 'Location'),
            'Visual style': infer_or_value(skip_custom(safe_get(result, 'Visual style')), 'Visual style'),
            'lighting': infer_or_value(skip_custom(safe_get(result, 'lighting')), 'lighting'),
            'type': infer_or_value(prompt_type, 'type'),
            'time': infer_or_value(time, 'time'),
            'main_character': infer_or_value(skip_custom(main_character), 'main_character'),
            'extra_desc': infer_or_value(extra_desc, 'extra_desc')
        }
        
        # Only add ending if user requested it
        if include_ending:
            prompt_json['ending'] = infer_or_value(skip_custom(safe_get(result, 'ending')), 'ending')
        
        # Only add camera motion for video prompts
        if prompt_type == 'video':
            prompt_json['camera motion'] = infer_or_value(skip_custom(safe_get(result, 'camera motion')), 'camera motion')
        
        print(f"[DEBUG] prompt_json: {prompt_json}")
        # 重新組合 json 內容為一篇可讀性高的作品
        def time_to_chinese(tstr):
            if not tstr or ':' not in tstr:
                return ''
            h, m = tstr.split(':')
            h = int(h)
            if 5 <= h < 8:
                return '黎明'
            elif 8 <= h < 12:
                return '上午'
            elif 12 <= h < 13:
                return '中午'
            elif 13 <= h < 17:
                return '下午'
            elif 17 <= h < 19:
                return '傍晚'
            elif 19 <= h < 23:
                return '晚上'
            elif h == 0:
                return '午夜'
            elif 23 <= h < 24:
                return '深夜'
            else:
                return ''

        import json
        zh_time = time_to_chinese(prompt_json.get('time'))
        prompt_json_for_gemini = dict(prompt_json)
        if zh_time:
            prompt_json_for_gemini['time'] = zh_time
        # Gemini prompt 語言
        lang_map = {
            'en': 'English',
            'zh-TW': 'Traditional Chinese',
            'zh-CN': 'Simplified Chinese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'fr': 'French',
            'de': 'German',
            'es': 'Spanish'
        }
        prompt_lang = lang_map.get(output_lang, 'English')
        if output_lang == 'en':
            if creative_mode:
                prompt_for_gemini = f"Please rewrite the following JSON content into a highly readable, natural, and fluent {prompt_lang} description, omitting all field titles and separators, and arranging the order logically. CREATIVE MODE: Use poetic, artistic, and evocative language. Make the description cinematically rich, emotionally engaging, and visually stunning with bold artistic expressions: {json.dumps(prompt_json_for_gemini, ensure_ascii=False)}"
            else:
                prompt_for_gemini = f"Please rewrite the following JSON content into a highly readable, natural, and fluent {prompt_lang} description, omitting all field titles and separators, and arranging the order logically: {json.dumps(prompt_json_for_gemini, ensure_ascii=False)}"
        else:
            if creative_mode:
                prompt_for_gemini = f"請根據以下 json 內容，重新組合成一篇可讀性高、自然流暢的{prompt_lang}作品，省略所有欄位標題與分隔符，並根據內容合理安排先後次序。創意模式：使用詩意、藝術性和令人回味的語言。讓描述富有電影感、情感豐富且視覺震撼，以大膽的藝術表達呈現：{json.dumps(prompt_json_for_gemini, ensure_ascii=False)}"
            else:
                prompt_for_gemini = f"請根據以下 json 內容，重新組合成一篇可讀性高、自然流暢的{prompt_lang}作品，省略所有欄位標題與分隔符，並根據內容合理安排先後次序：{json.dumps(prompt_json_for_gemini, ensure_ascii=False)}"
        print(f"[DEBUG] Gemini prompt: {prompt_for_gemini}")
        api_key = os.getenv('GEMINI_API_KEY', 'YOUR_API_KEY')
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt_for_gemini}
                    ]
                }
            ]
        }
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": api_key
        }
        print(f"[DEBUG] Gemini API payload (prompt): {payload}")
        resp2 = requests.post(url, json=payload, headers=headers)
        print(f"[DEBUG] Gemini API status (prompt): {resp2.status_code}")
        try:
            resp2_json = resp2.json()
            print(f"[DEBUG] Gemini API response (prompt): {resp2_json}")
            prompt_text = resp2_json['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            print(f"[DEBUG] Gemini API parse error (prompt): {e}")
            prompt_text = ''
    import json
    prompt_json_str = None
    # 僅在 prompt_json 有內容時才生成
    def is_all_infer_or_default(j):
        if not j:
            return True
        
        # Define infer keys based on prompt type and user preferences
        base_infer_keys = [
            'Scene', 'ambiance_or_mood', 'Location', 'Visual style', 'lighting', 'main_character', 'extra_desc'
        ]
        
        # Add ending only if user requested it
        if 'ending' in j:
            base_infer_keys.append('ending')
        
        # Add camera motion only for video prompts
        infer_keys = base_infer_keys.copy()
        if j.get('type') == 'video':
            infer_keys.append('camera motion')
        
        for k in infer_keys:
            v = j.get(k, '')
            # Convert to string if it's not already, then check
            if v and isinstance(v, str) and not v.startswith('[Please infer'):
                return False
            elif v and not isinstance(v, str):
                # If it's not a string and not empty, it's valid content
                return False
        
        # Check if type and time are default values
        prompt_type = j.get('type', '')
        if prompt_type not in ['image', 'video']:
            return False
        if j.get('time', '') != '00:00':
            return False
        return True

    valid_json = prompt_json and not is_all_infer_or_default(prompt_json)
    print(f"[DEBUG] valid_json: {valid_json}")
    
    # Generate images automatically only when explicitly requested.
    # We intentionally DO NOT start the image generation (which connects to ComfyUI/WebSocket)
    # during the initial "Generate Prompt" POST so the user first sees the composed
    # Complete Prompt and JSON for review/editing. Image generation will run only when
    # the front-end triggers the regenerate action (which POSTs action=regenerate),
    # or when the form includes auto_generate=true. Default is disabled to avoid
    # starting WebSocket connections before the user confirms.
    generated_images = None
    auto_generate = request.form.get('auto_generate') == 'true'
    if (COMFYUI_AVAILABLE and prompt_json and valid_json and auto_generate):
        try:
            print("[DEBUG] Starting automatic image generation...")
            generated_image_paths = generate_from_vprompt_dict(
                prompt_json, 
                output_dir="./uploads/generated"
            )
            
            if generated_image_paths:
                print(f"[DEBUG] Generated {len(generated_image_paths)} images: {generated_image_paths}")
            else:
                print("[DEBUG] No images were generated")
                generated_images = {"success": False, "error": "No images generated"}
                
        except Exception as e:
            print(f"[DEBUG] Image generation failed: {str(e)}")
            generated_images = {"success": False, "error": str(e)}
    else:
        if not COMFYUI_AVAILABLE:
            print("[DEBUG] Image generation service not available, skipping image generation")
        elif not prompt_json or not valid_json:
            print("[DEBUG] No valid JSON prompt, skipping image generation")
    
    # Only show prompt_text and prompt_json after POST or AJAX
    if request.method == 'POST':
        if valid_json:
            prompt_json_str = json.dumps(prompt_json, ensure_ascii=False, indent=2)
            print(f"[DEBUG] prompt_json_str: {prompt_json_str}")
        else:
            print("[DEBUG] No valid prompt_json, but keep prompt_text if present.")
            prompt_json_str = None
        print(f"[DEBUG] Final prompt_text: {prompt_text}")
        print(f"[DEBUG] Passing to template: prompt_text={prompt_text is not None}, prompt_json={prompt_json is not None}, prompt_json_str={prompt_json_str is not None}, image_url={image_url}, generated_images={generated_images}")
    else:
        prompt_text = ''
        prompt_json = None
        prompt_json_str = ''

    # Prepare template context
    context = dict(
        prompt_text=prompt_text if prompt_text else '',
        prompt_json=prompt_json if prompt_json else None,
        prompt_json_str=prompt_json_str if prompt_json_str else '',
        image_url=image_url if image_url else '',
        generated_images=generated_images if generated_images else None,
        prompt_type=prompt_type,
        output_lang=output_lang_display,
        time=time,
        scene=scene,
        custom_scene=custom_scene,
        character=character,
        custom_character=custom_character,
        extra_desc=extra_desc,
        creative_mode=creative_mode,
        include_ending=include_ending,
        multiple_scenes=multiple_scenes,
        seed=locals().get('seed', None)
    )

    # Decide whether to render full page or only results fragment for AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if is_ajax and request.method == 'POST':
        resp = make_response(render_template('_results.html', **context))
    else:
        resp = make_response(render_template('index.html', **context))

    # Set cookies for POST
    if request.method == 'POST':
        # Only store user input values, not rendered content
        if prompt_type is not None:
            resp.set_cookie('prompt_type', prompt_type)
        if output_lang is not None:
            resp.set_cookie('output_lang', output_lang_display)
        if time is not None:
            resp.set_cookie('time', time)
        resp.set_cookie('scene', scene if scene is not None else '')
        resp.set_cookie('custom_scene', custom_scene if custom_scene is not None else '')
        resp.set_cookie('character', character if character is not None else '')
        resp.set_cookie('custom_character', custom_character if custom_character is not None else '')
        resp.set_cookie('extra_desc', extra_desc if extra_desc is not None else '')
        resp.set_cookie('creative_mode', 'true' if creative_mode else 'false')
        resp.set_cookie('include_ending', 'true' if include_ending else 'false')
        resp.set_cookie('multiple_scenes', 'true' if multiple_scenes else 'false')
        resp.set_cookie('bypass_time', str(bypass_time).lower())

        # Log user interaction if we have results
        if prompt_text or prompt_json:
            print(f"[DEBUG] Logging user interaction: prompt_text exists: {prompt_text is not None}, prompt_json exists: {prompt_json is not None}")
            user_inputs = {
                'prompt_type': prompt_type,
                'output_lang': output_lang,
                'time': time,
                'scene': scene,
                'custom_scene': custom_scene,
                'character': character,
                'custom_character': custom_character,
                'extra_desc': extra_desc,
                'creative_mode': creative_mode,
                'include_ending': include_ending,
                'multiple_scenes': multiple_scenes
            }

            # Fix image_path scope issue - get it from the local context
            uploaded_file_path = image_path if 'image_path' in locals() else None

            log_user_interaction(
                user_inputs=user_inputs,
                prompt_result=prompt_text,
                prompt_json_result=prompt_json,
                uploaded_file_path=uploaded_file_path,
                generated_images=generated_images
            )

    return resp


def _background_generate(job_id, prompt_json, seed=None):
    """Background worker that runs image generation without progress tracking."""
    logger = logging.getLogger(__name__)
    logger.info("Background generate started for job %s", job_id)

    try:
        # Set initial status to processing
        with generation_jobs_lock:
            generation_jobs[job_id]['status'] = 'processing'
            generation_jobs[job_id]['progress'] = 0

        # Call the actual generation function (this may take time)
        generated_paths = []

        logger.info("Job %s: COMFYUI_AVAILABLE = %s", job_id, COMFYUI_AVAILABLE)

        if COMFYUI_AVAILABLE:
            # Call integration function without progress callback to avoid blocking
            try:
                logger.info("Job %s: Calling generate_from_vprompt_dict with progress tracking", job_id)
                
                # Define progress callback to update job progress
                def update_progress(progress_percent):
                    try:
                        with generation_jobs_lock:
                            if job_id in generation_jobs:
                                generation_jobs[job_id]['progress'] = progress_percent
                                logger.debug("Job %s progress updated to %d%%", job_id, progress_percent)
                    except Exception as e:
                        logger.debug("Failed to update progress for job %s: %s", job_id, e)
                
                generated_paths = generate_from_vprompt_dict(
                    prompt_json,
                    output_dir=GENERATED_FOLDER,
                    seed=seed,
                    progress_callback=update_progress
                )
                logger.info("Job %s generation completed, result: %s", job_id, generated_paths)
            except Exception as e:
                logger.exception("Generation failed for job %s: %s", job_id, e)
                with generation_jobs_lock:
                    generation_jobs[job_id]['status'] = 'error'
                    generation_jobs[job_id]['error'] = str(e)
                return
        else:
            # Simulate generation fallback
            logger.info("ComfyUI not available, simulating generation")
            time.sleep(2)  # Simple delay instead of progress updates
            generated_paths = []

        logger.info("Job %s generation completed, saving results", job_id)

        # Save results
        images_info = []
        if not generated_paths:
            logger.warning("Job %s: No generated paths returned", job_id)
            generated_paths = []
        else:
            logger.info("Job %s: Generated paths: %s", job_id, generated_paths)

        # Always add image info if a path is returned, bypass existence check
        for img_path in generated_paths:
            filename = os.path.basename(img_path)
            images_info.append({
                'filename': filename,
                'url': f"/uploads/generated/{filename}",
                'path': img_path
            })

        # Only set job status to done if all images exist
        if not generated_paths:
            logger.warning(f"[IMAGE DEBUG] Job {job_id}: No generated paths returned, setting status to error")
            with generation_jobs_lock:
                generation_jobs[job_id]['status'] = 'error'
                generation_jobs[job_id]['error'] = 'No image paths returned after generation.'
                generation_jobs[job_id]['progress'] = 100
                generation_jobs[job_id]['images'] = images_info
        else:
            logger.info("Job %s processed %d images, setting status to done", job_id, len(images_info))
            try:
                with generation_jobs_lock:
                    old_progress = generation_jobs[job_id]['progress']
                    generation_jobs[job_id]['progress'] = 100
                    generation_jobs[job_id]['status'] = 'done'
                    generation_jobs[job_id]['images'] = images_info
                    logger.info("Job %s completion: progress %d%% -> 100%%, status set to done", job_id, old_progress)
            except Exception as e:
                logger.exception("Error setting job completion status for job %s: %s", job_id, e)
                # Try to set error status
                with generation_jobs_lock:
                    generation_jobs[job_id]['status'] = 'error'
                    generation_jobs[job_id]['error'] = f"Completion error: {str(e)}"

        logger.info("Job %s processed %d images, setting status to done", job_id, len(images_info))

        try:
            with generation_jobs_lock:
                old_progress = generation_jobs[job_id]['progress']
                generation_jobs[job_id]['progress'] = 100
                generation_jobs[job_id]['status'] = 'done'
                generation_jobs[job_id]['images'] = images_info
                logger.info("Job %s completion: progress %d%% -> 100%%, status set to done", job_id, old_progress)
        except Exception as e:
            logger.exception("Error setting job completion status for job %s: %s", job_id, e)
            # Try to set error status
            with generation_jobs_lock:
                generation_jobs[job_id]['status'] = 'error'
                generation_jobs[job_id]['error'] = f"Completion error: {str(e)}"

        logger.info("Job %s marked done, %d images", job_id, len(images_info))

    except Exception as e:
        logger.exception("Unhandled error in background_generate for job %s: %s", job_id, e)
        with generation_jobs_lock:
            generation_jobs[job_id]['status'] = 'error'
            generation_jobs[job_id]['error'] = str(e)


@app.route('/start_generation', methods=['POST'])
def start_generation():
    try:
        # Get the JSON data from the request - handle both JSON and FormData
        json_data = None
        if request.is_json:
            json_data = request.get_json()
        else:
            # Handle FormData
            json_data_str = request.form.get('json_data')
            if json_data_str:
                json_data = json.loads(json_data_str)

        if not json_data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Get optional seed parameter
        seed = None
        if request.is_json:
            json_data_req = request.get_json(silent=True)
            if json_data_req and 'seed' in json_data_req:
                seed = json_data_req.get('seed')
        else:
            seed_str = request.form.get('seed')
            if seed_str:
                try:
                    seed = int(seed_str)
                except (ValueError, TypeError):
                    return jsonify({"error": "Invalid seed value"}), 400

        # Generate a unique job ID
        job_id = str(uuid.uuid4())

        # Initialize the job in the global jobs dictionary
        with generation_jobs_lock:
            generation_jobs[job_id] = {
                'status': 'pending',
                'progress': 0,
                'images': [],
                'error': None,
                'seed': seed,  # Store seed for reference
                'prompt_json': json_data  # Store prompt for debug/log
            }

        # Start background generation thread
        thread = threading.Thread(target=_background_generate, args=(job_id, json_data, seed))
        thread.daemon = True
        thread.start()

        # Return the job ID immediately
        return jsonify({"job_id": job_id, "seed": seed}), 200

    except json.JSONDecodeError as e:
        logger = logging.getLogger(__name__)
        logger.exception("Error in start_generation")
        return jsonify({"error": f"Invalid JSON format: {str(e)}"}), 400
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Error in start_generation")
        return jsonify({"error": str(e)}), 500


@app.route('/generation_status/<job_id>')
def generation_status(job_id):
    logger = logging.getLogger(__name__)
    with generation_jobs_lock:
        job = generation_jobs.get(job_id)
    if job:
        logger.debug("Status request for job %s: %s", job_id, job.get('status'))
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    resp_dict = {
        'status': job['status'],
        'progress': job['progress'],
        'error': job.get('error'),
        'prompt_json': job.get('prompt_json')
    }
    # If job is done, include images
    if job['status'] == 'done':
        resp_dict['images'] = job.get('images', [])
    response = jsonify(resp_dict)
    # Prevent caching of status responses
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/generation_result/<job_id>')
def generation_result(job_id):
    with generation_jobs_lock:
        job = generation_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    if job['status'] != 'done':
        return jsonify({'error': 'Job not completed', 'status': job['status']}), 400
    return jsonify({'images': job.get('images', [])}), 200


@app.route('/regeneration_result/<job_id>')
def regeneration_result(job_id):
    """Get regeneration results and return HTML for frontend"""
    with generation_jobs_lock:
        job = generation_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    if job['status'] != 'done':
        return jsonify({'error': 'Job not completed', 'status': job['status']}), 400

    images = job.get('images', [])
    if not images:
        return jsonify({'error': 'No images generated'}), 400

    # Return HTML response for frontend, with debug JSON output
    import json
    response_html = f"""
    <div>
        <h2 data-en='Generated Images ({len(images)})' data-zh='生成的圖片 ({len(images)})'>Generated Images ({len(images)})</h2>
        <div class='generated-images-gallery'>
    """

    for image in images:
        response_html += f"""
            <div class='generated-image-item'>
                <img src='{image['url']}' alt='Generated image' class='generated-image-preview' onclick="openImageModal('{image['url']}', '{image['filename']}')">
                <div class='image-filename'>{image['filename']}</div>
            </div>
        """

    response_html += """
        </div>
    </div>
    """

    return response_html

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/uploads/generated/<filename>')
def generated_file(filename):
    """Serve generated image files with caching headers for better performance"""
    response = send_file(os.path.join(GENERATED_FOLDER, filename))
    # Add cache headers to improve loading speed
    response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
    return response

@app.route('/convert_heic_preview', methods=['POST'])
def convert_heic_preview():
    """Convert uploaded HEIC file to JPEG for immediate preview"""
    try:
        import pillow_heif
        from PIL import Image
        import io
        
        # Register HEIF opener with Pillow
        pillow_heif.register_heif_opener()
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '' or file.filename is None:
            return jsonify({'error': 'No file selected'}), 400
            
        # Check if file is HEIC/HEIF
        filename = file.filename.lower()
        if not filename.endswith(('.heic', '.heif')):
            return jsonify({'error': 'Not a HEIC/HEIF file'}), 400
            
        # Read file content
        file_content = file.read()
        
        # Open and convert HEIC to JPEG
        with Image.open(io.BytesIO(file_content)) as img:
            # Convert to RGB if necessary
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # Create thumbnail for preview (max 600x400 for faster loading)
            img.thumbnail((600, 400), Image.Resampling.LANCZOS)
            
            # Save as JPEG to memory
            img_io = io.BytesIO()
            img.save(img_io, 'JPEG', quality=80, optimize=True)
            img_io.seek(0)
            
            # Return as response
            return send_file(
                img_io,
                mimetype='image/jpeg',
                as_attachment=False
            )
            
    except ImportError:
        return jsonify({'error': 'HEIC support not available on server'}), 501
    except Exception as e:
        print(f"[ERROR] HEIC preview conversion failed: {e}")
        return jsonify({'error': 'Preview conversion failed', 'details': str(e)}), 500

@app.route('/convert_heic/<filename>')
def convert_heic(filename):
    """Convert HEIC file to JPEG for preview"""
    try:
        import pillow_heif
        from PIL import Image
        import io
        
        # Register HEIF opener with Pillow
        pillow_heif.register_heif_opener()
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
            
        # Check if file is HEIC/HEIF
        if not filename.lower().endswith(('.heic', '.heif')):
            return jsonify({'error': 'Not a HEIC/HEIF file'}), 400
            
        # Open and convert HEIC to JPEG
        with Image.open(file_path) as img:
            # Convert to RGB if necessary
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # Create thumbnail for preview (max 800x600)
            img.thumbnail((800, 600), Image.Resampling.LANCZOS)
            
            # Save as JPEG to memory
            img_io = io.BytesIO()
            img.save(img_io, 'JPEG', quality=85, optimize=True)
            img_io.seek(0)
            
            # Return as response
            return send_file(
                img_io,
                mimetype='image/jpeg',
                as_attachment=False,
                download_name=f"{os.path.splitext(filename)[0]}_preview.jpg"
            )
            
    except ImportError:
        return jsonify({'error': 'HEIC support not available on server'}), 501
    except Exception as e:
        print(f"[ERROR] HEIC conversion failed: {e}")
        return jsonify({'error': 'Conversion failed', 'details': str(e)}), 500

@app.route('/heic_info/<filename>')
def heic_info(filename):
    """Get HEIC file information"""
    try:
        import pillow_heif
        from PIL import Image
        
        # Register HEIF opener with Pillow
        pillow_heif.register_heif_opener()
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
            
        # Check if file is HEIC/HEIF
        if not filename.lower().endswith(('.heic', '.heif')):
            return jsonify({'error': 'Not a HEIC/HEIF file'}), 400
            
        # Get image info
        with Image.open(file_path) as img:
            info = {
                'filename': filename,
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                'width': img.width,
                'height': img.height,
                'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
            }
            
            # Add EXIF data if available
            try:
                exif = img.getexif()
                info['has_exif'] = len(exif) > 0
            except:
                info['has_exif'] = False
                
            return jsonify(info)
            
    except ImportError:
        return jsonify({'error': 'HEIC support not available on server'}), 501
    except Exception as e:
        print(f"[ERROR] HEIC info extraction failed: {e}")
        return jsonify({'error': 'Info extraction failed', 'details': str(e)}), 500

@app.route('/download_prompt')
def download_prompt():
    from flask import Response
    prompt = request.args.get('prompt', '')
    return Response(prompt, mimetype='text/plain; charset=utf-8', headers={
        'Content-Disposition': 'attachment; filename=prompt.txt'
    })

@app.route('/download_json')
def download_json():
    import json
    from flask import Response
    import urllib.parse
    prompt_json = request.args.get('prompt_json')
    # 解析 query string 傳來的 JSON 字串
    if prompt_json:
        try:
            data = json.loads(urllib.parse.unquote(prompt_json))
        except Exception:
            data = prompt_json
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        json_str = '{}'
    return Response(json_str, mimetype='application/json; charset=utf-8', headers={
        'Content-Disposition': 'attachment; filename=prompt.json'
    })

def gemini_2_flash_api(image_path, api_key):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": "請詳細識別這張圖片，並以 json 格式輸出：Scene、ambiance_or_mood、Location、Visual style、camera motion、lighting、ending。"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                ]
            }
        ]
    }
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()
@app.route('/test_heic.html')
def test_heic():
    return send_from_directory('.', 'test_heic.html')

# Initialize the ComfyUI model during server startup
cached_model = None

def initialize_model():
    global cached_model
    logger = logging.getLogger(__name__)
    if cached_model is None:
        cached_model = ComfyUIClient()  # Replace with actual model loading logic
        logger.info("ComfyUI model loaded and cached.")

if __name__ == '__main__':
    # Configuration for network access
    host = os.getenv('HOST', '0.0.0.0')  # 0.0.0.0 allows network access
    port = int(os.getenv('PORT', 5001))
    debug = False  # Disable debug mode to avoid reloader issues
    
    print(f"🚀 Starting vPrompt server...")
    print(f"📡 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🐛 Debug: {debug}")
    print(f"🌐 Access URLs:")
    print(f"   Local:   http://localhost:{port}")
    if host == '0.0.0.0':
        print(f"   Network: http://[your-ip-address]:{port}")
    print("🎯 Ready to generate creative prompts!")
    
    app.run(debug=debug, host=host, port=port)
