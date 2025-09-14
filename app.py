import os
import json
import logging
from datetime import datetime

# Configure logging to show INFO messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
except ImportError as e:
    try:
        from api.simple_integration import generate_from_vprompt_dict
        COMFYUI_AVAILABLE = True
    except ImportError as e2:
        COMFYUI_AVAILABLE = False

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
        pass
    
    return {
        'country': 'Unknown',
        'region': 'Unknown', 
        'city': 'Unknown',
        'timezone': 'Unknown',
        'isp': 'Unknown'
    }

def log_user_interaction(user_inputs, prompt_result, prompt_json_result, uploaded_file_path=None, generated_images=None):
    """Log user interaction to JSON file"""
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
        
        
    except Exception as e:
        pass

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
        

        
        # Check if no image uploaded and "Share your thoughts" is empty, set default prompt
        if not file and not extra_desc.strip():
            extra_desc = 'Cinematic, Asian beautiful girl standing in the street, Thousand of Nano Banana Falling from sky.'
        
        # 若所有欄位皆空，直接清空結果
        if not any([prompt_type, output_lang, scene, custom_scene, character, custom_character, extra_desc, file]):
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
                'zh-CN': 'Simplified Chinese'
            }
            prompt_lang = lang_map.get(output_lang, 'English')
            # Language-specific prompts for image recognition
            if output_lang == 'en':
                if prompt_type == 'video':
                    if creative_mode:
                        prompt_text_recog = f"Please analyze this image in detail and output video content in JSON format: Scene, ambiance_or_mood, Location, Visual style, camera motion, lighting{', ending' if include_ending else ''}. Creative Mode: Be highly creative, artistic, and experimental. For 'camera motion', suggest bold, innovative, and cinematic camera movements that push creative boundaries (e.g., 'surreal spiral descent around subject', 'time-delayed tracking through ethereal space', 'anti-gravity orbital shot', 'dreamlike morphing perspective', 'kaleidoscopic rotation sequence', 'poetic flowing transition'). Make the visuals stunning and emotionally powerful. All responses must be in {prompt_lang}."
                    else:
                        prompt_text_recog = f"Please analyze this image in detail and output video content in JSON format: Scene, ambiance_or_mood, Location, Visual style, camera motion, lighting{', ending' if include_ending else ''}. For 'camera motion', suggest creative and cinematic camera movements based on the scene (e.g., tracking shot, crane movement, handheld intimacy, aerial shot, push-pull shot, dolly movement, rotation, etc.). All responses must be in {prompt_lang}."
                else:
                    if creative_mode:
                        prompt_text_recog = f"Please analyze this image in detail and output in JSON format: Scene, ambiance_or_mood, Location, Visual style, lighting{', ending' if include_ending else ''}. Creative Mode: Be highly artistic, experimental, and imaginative. Push creative boundaries with bold visual concepts, unconventional perspectives, and innovative storytelling approaches. All responses must be in {prompt_lang}."
                    else:
                        prompt_text_recog = f"Please analyze this image in detail and output in JSON format: Scene, ambiance_or_mood, Location, Visual style, lighting{', ending' if include_ending else ''}. All responses must be in {prompt_lang}."
            elif output_lang == 'zh-CN':
                if prompt_type == 'video':
                    if creative_mode:
                        prompt_text_recog = f"请详细识别这张图片，并以 json 格式输出视频内容：Scene、ambiance_or_mood、Location、Visual style、camera motion、lighting{'、ending' if include_ending else ''}。创意模式：请极具创意、艺术性和实验性。对于 'camera motion'，请建议大胆、创新且具电影感的摄影机运动，突破创意界限（例如：'围绕主体的超现实螺旋下降'、'穿越飘渺空间的时间延迟追踪'、'反重力轨道镜头'、'梦幻般的变形视角'、'万花筒式旋转序列'、'诗意流动转场'）。让画面视觉震撼且情感强烈。所有回应内容一律使用{prompt_lang}。"
                    else:
                        prompt_text_recog = f"请详细识别这张图片，并以 json 格式输出视频内容：Scene、ambiance_or_mood、Location、Visual style、camera motion、lighting{'、ending' if include_ending else ''}。对于 'camera motion'，请根据场景建议富有创意和电影感的摄影机运动（例如：追踪镜头、升降运动、手持亲密感、空拍镜头、推拉镜头、移动推轨、旋转等）。所有回应内容一律使用{prompt_lang}。"
                else:
                    if creative_mode:
                        prompt_text_recog = f"请详细识别这张图片，并以 json 格式输出：Scene、ambiance_or_mood、Location、Visual style、lighting{'、ending' if include_ending else ''}。创意模式：请极具艺术性、实验性和想象力。以大胆的视觉概念、非传统的视角和创新的故事叙述方式突破创意界限。所有回应内容一律使用{prompt_lang}。"
                    else:
                        prompt_text_recog = f"请详细识别这张图片，并以 json 格式输出：Scene、ambiance_or_mood、Location、Visual style、lighting{'、ending' if include_ending else ''}。所有回应内容一律使用{prompt_lang}。"
            else:  # zh-TW and other languages
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
            resp = requests.post(url, json=payload, headers=headers)
            import re, json as pyjson
            try:
                resp_json = resp.json()
                text = resp_json['candidates'][0]['content']['parts'][0]['text']
            except Exception as e:
                text = ''
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    parsed_result = pyjson.loads(match.group())
                    # Extract the content from nested structure if present
                    if 'VIDEO' in parsed_result:
                        result = parsed_result['VIDEO']
                    elif 'IMAGE' in parsed_result:
                        result = parsed_result['IMAGE']
                    else:
                        result = parsed_result
                except Exception as e:
                    result = None
            else:
                result = None
            # 若 result 為 None，則用空欄位
            if not result:
                if prompt_type == 'video':
                    result = {'Scene': '', 'ambiance_or_mood': '', 'Location': '', 'Visual style': '', 'camera motion': '', 'lighting': '', 'ending': ''}
                else:
                    result = {'Scene': '', 'ambiance_or_mood': '', 'Location': '', 'Visual style': '', 'lighting': '', 'ending': ''}
        else:
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
                    'zh-CN': 'Simplified Chinese'
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
                elif output_lang == 'zh-CN':
                    if prompt_type == 'video':
                        if creative_mode:
                            scene_instruction = "创建多个连续场景序列" if multiple_scenes else "只创建单一场景"
                            enhance_prompt = f"根据这些用户输入: {user_input_text}，请创建一个专为视频内容设计的详细 JSON，包含以下栏位：Scene、ambiance_or_mood、Location、Visual style、camera motion、lighting{'、ending' if include_ending else ''}。重要：{scene_instruction}。对于 'camera motion' 栏位，请只选择一种特定的摄影机运动 - 不要组合多个镜头。创造一个大胆、富有想象力且非传统的摄影机运动，突破创意界限（例如：'穿越不可能几何体的超现实漂浮' 或 '围绕情感的时间扭曲螺旋舞蹈' 或 '反重力液态水银流动' 或 '梦境逻辑视角变形' - 只选择其中一种）。让它视觉震撼、情感强烈且艺术性突破。请用{prompt_lang}回应，并只输出有效的 JSON 格式。"
                        else:
                            scene_instruction = "创建多个连续场景序列" if multiple_scenes else "只创建单一场景"
                            enhance_prompt = f"根据这些用户输入: {user_input_text}，请创建一个专为视频内容设计的详细 JSON，包含以下栏位：Scene、ambiance_or_mood、Location、Visual style、camera motion、lighting{'、ending' if include_ending else ''}。重要：{scene_instruction}。对于 'camera motion' 栏位，请只选择一种特定的摄影机运动 - 不要组合多个镜头。创造一个富有创意和电影感的摄影机运动，增强故事叙述效果（例如：'平滑追踪镜头跟随主体' 或 '戏剧性升降镜头展现风景' 或 '亲密手持特写' 或 '扫描式空拍镜头' - 只选择其中一种）。让摄影机运动具体、有电影感且富有情感张力。请用{prompt_lang}回应，并只输出有效的 JSON 格式。"
                    else:
                        if creative_mode:
                            scene_instruction = "创建多个连续场景序列" if multiple_scenes else "只创建单一场景"
                            enhance_prompt = f"根据这些用户输入: {user_input_text}，请创建一个详细的 JSON，包含以下栏位：Scene、ambiance_or_mood、Location、Visual style、lighting{'、ending' if include_ending else ''}。重要：{scene_instruction}。创意模式：请极具艺术性、实验性和想象力。以大胆的视觉概念、非传统的视角、超现实元素和创新的故事叙述方式突破创意界限。为缺少的栏位填入突破性的创意细节。请用{prompt_lang}回应，并只输出有效的 JSON 格式。"
                        else:
                            scene_instruction = "创建多个连续场景序列" if multiple_scenes else "只创建单一场景"
                            enhance_prompt = f"根据这些用户输入: {user_input_text}，请创建一个详细的 JSON，包含以下栏位：Scene、ambiance_or_mood、Location、Visual style、lighting{'、ending' if include_ending else ''}。重要：{scene_instruction}。为缺少的栏位填入富有创意且合适的细节。请用{prompt_lang}回应，并只输出有效的 JSON 格式。"
                else:  # zh-TW and other languages
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
                    resp = requests.post(url, json=payload, headers=headers)
                    
                    if resp.status_code == 200:
                        import re, json as pyjson
                        resp_json = resp.json()
                        text = resp_json['candidates'][0]['content']['parts'][0]['text']
                        
                        # Extract JSON from response
                        match = re.search(r'\{[\s\S]*\}', text)
                        if match:
                            try:
                                enhanced_result = pyjson.loads(match.group())
                                # Extract the content from nested structure if present
                                if 'VIDEO' in enhanced_result:
                                    result = enhanced_result['VIDEO']
                                elif 'IMAGE' in enhanced_result:
                                    result = enhanced_result['IMAGE']
                                else:
                                    result = enhanced_result
                            except Exception as e:
                                # Keep the original result if parsing fails
                                pass
                        else:
                            pass
                    else:
                        pass
                        
                except Exception as e:
                    # Keep the original result if API call fails
                    pass
        
        # 確保 result 總是有預設值，防止 KeyError
        if 'result' not in locals() or result is None:
            result = {
                'Scene': '',
                'ambiance_or_mood': '',
                'Location': '',
                'Visual style': '',
                'camera motion': '',
                'lighting': '',
                'ending': ''
            }
        

        
        # 確保 result 包含所有必要的鍵
        default_keys = ['Scene', 'ambiance_or_mood', 'Location', 'Visual style', 'camera motion', 'lighting']
        if include_ending:
            default_keys.append('ending')
        for key in default_keys:
            if key not in result:
                result[key] = ''
        
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
        # Gemini prompt 語言 (handle case insensitive)
        lang_map = {
            'en': 'English',
            'zh-TW': 'Traditional Chinese',
            'zh-CN': 'Simplified Chinese',
            'zh-tw': 'Traditional Chinese',  # lowercase variant
            'zh-cn': 'Simplified Chinese'  # lowercase variant
        }
        prompt_lang = lang_map.get(output_lang, 'English')
        if output_lang == 'en':
            if creative_mode:
                prompt_for_gemini = f"Please rewrite the following JSON content into a highly readable, natural, and fluent {prompt_lang} description, omitting all field titles and separators, and arranging the order logically. CREATIVE MODE: Use poetic, artistic, and evocative language. Make the description cinematically rich, emotionally engaging, and visually stunning with bold artistic expressions: {json.dumps(prompt_json_for_gemini, ensure_ascii=False)}"
            else:
                prompt_for_gemini = f"Please rewrite the following JSON content into a highly readable, natural, and fluent {prompt_lang} description, omitting all field titles and separators, and arranging the order logically: {json.dumps(prompt_json_for_gemini, ensure_ascii=False)}"
        elif output_lang in ['zh-CN', 'zh-cn']:
            if creative_mode:
                prompt_for_gemini = f"请根据以下 json 内容，重新组合成一篇可读性高、自然流畅的{prompt_lang}作品，省略所有栏位标题与分隔符，并根据内容合理安排先后次序。创意模式：使用诗意、艺术性和令人回味的语言。让描述富有电影感、情感丰富且视觉震撼，以大胆的艺术表达呈现。请务必使用简体中文回复，不要使用任何英文单词或短语：{json.dumps(prompt_json_for_gemini, ensure_ascii=False)}"
            else:
                prompt_for_gemini = f"请根据以下 json 内容，重新组合成一篇可读性高、自然流畅的{prompt_lang}作品，省略所有栏位标题与分隔符，并根据内容合理安排先后次序。请务必使用简体中文回复，不要使用任何英文单词或短语：{json.dumps(prompt_json_for_gemini, ensure_ascii=False)}"
        else:  # zh-TW and other languages
            if creative_mode:
                prompt_for_gemini = f"請根據以下 json 內容，重新組合成一篇可讀性高、自然流暢的{prompt_lang}作品，省略所有欄位標題與分隔符，並根據內容合理安排先後次序。創意模式：使用詩意、藝術性和令人回味的語言。讓描述富有電影感、情感豐富且視覺震撼，以大膽的藝術表達呈現：{json.dumps(prompt_json_for_gemini, ensure_ascii=False)}"
            else:
                prompt_for_gemini = f"請根據以下 json 內容，重新組合成一篇可讀性高、自然流暢的{prompt_lang}作品，省略所有欄位標題與分隔符，並根據內容合理安排先後次序：{json.dumps(prompt_json_for_gemini, ensure_ascii=False)}"

        api_key = os.getenv('GEMINI_API_KEY', 'YOUR_API_KEY')
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        
        # Add system instruction to enforce language output
        system_instruction = ""
        if output_lang in ['zh-CN', 'zh-cn']:
            system_instruction = "You must respond ONLY in Simplified Chinese (简体中文). Do not use any English words or phrases in your response."
        elif output_lang in ['zh-TW', 'zh-tw']:
            system_instruction = "You must respond ONLY in Traditional Chinese (繁體中文). Do not use any English words or phrases in your response."
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt_for_gemini}
                    ]
                }
            ]
        }
        
        # Add system instruction if needed
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [
                    {"text": system_instruction}
                ]
            }
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": api_key
        }
        resp2 = requests.post(url, json=payload, headers=headers)
        try:
            resp2_json = resp2.json()
            prompt_text = resp2_json['candidates'][0]['content']['parts'][0]['text']
            
            # Debug logging to track API response
            logger = logging.getLogger(__name__)
            logger.info(f"Gemini API Request - Language: {output_lang}, Prompt Lang: {prompt_lang}")
            logger.info(f"Gemini API Request Prompt: {prompt_for_gemini[:200]}...")
            logger.info(f"Gemini API Response: {prompt_text[:200]}...")
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Gemini API Error: {str(e)}")
            logger.error(f"API Response: {resp2.text if resp2 else 'No response'}")
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
            # Get ComfyUI server configuration
            server_address = os.getenv('COMFYUI_SERVER_ADDRESS', '127.0.0.1')
            server_port = os.getenv('COMFYUI_SERVER_PORT', '8188')
            
            generated_image_paths = generate_from_vprompt_dict(
                prompt_json, 
                output_dir="./uploads/generated",
                server_address=server_address,
                port=server_port
            )
            
            if generated_image_paths:
                # Convert file paths to the format expected by the template
                images = []
                for image_path in generated_image_paths:
                    filename = os.path.basename(image_path)
                    image_url = url_for('generated_file', filename=filename)
                    images.append({
                        'url': image_url,
                        'filename': filename,
                        'path': image_path
                    })
                
                generated_images = {
                    "success": True,
                    "images": images,
                    "images_count": len(images)
                }
            else:
                generated_images = {"success": False, "error": "No images generated"}
                
        except Exception as e:
            generated_images = {"success": False, "error": str(e)}
    else:
        if not COMFYUI_AVAILABLE:
            pass
        elif not prompt_json or not valid_json:
            pass
    
    # Only show prompt_text and prompt_json after POST or AJAX
    if request.method == 'POST':
        if valid_json:
            prompt_json_str = json.dumps(prompt_json, ensure_ascii=False, indent=2)
        else:
            prompt_json_str = None
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
    
    # Add cache-busting headers to ensure fresh content
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'

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


def _background_voice_generate(job_id, text, voice_sample, emotion_params=None):
    """Background worker that runs IndexTTS voice generation with progress tracking."""
    if emotion_params is None:
        emotion_params = {}
    print(f"🎵 Background IndexTTS voice generate started for job {job_id} with voice sample {voice_sample}")
    print(f"🎭 Emotion parameters: {emotion_params}")
    
    try:
        # Direct IndexTTS API implementation (no imports from voice_integration)
        
        with generation_jobs_lock:
            if job_id not in generation_jobs:
                print(f"❌ Job {job_id} not found in generation_jobs")
                return
            generation_jobs[job_id]['status'] = 'processing'
            generation_jobs[job_id]['progress'] = 0
        
        print(f"🎵 Job {job_id}: Starting IndexTTS voice generation with voice sample {voice_sample}")
        
        # Define progress callback to update job progress
        def update_progress(progress_percent):
            try:
                with generation_jobs_lock:
                    if job_id in generation_jobs:
                        generation_jobs[job_id]['progress'] = progress_percent
                        print(f"🎵 Job {job_id} voice progress updated to {progress_percent}%")
            except Exception as e:
                print(f"❌ Failed to update voice progress for job {job_id}: {e}")
        
        # Use minimal voice generation approach (proven to work)
        import requests
        import uuid
        import os
        from datetime import datetime
        
        try:
            # Update progress
            update_progress(10)
            
            # Clean text
            cleaned_text = ' '.join(text.split())
            print(f"🎵 Generating voice from text using IndexTTS: {cleaned_text[:100]}{'...' if len(cleaned_text) > 100 else ''}")
            print(f"   Voice Sample: {voice_sample}")
            
            # Update progress
            update_progress(30)
            
            # IndexTTS server
            server_url = "http://192.168.68.30:8000"
            
            # Check server availability
            health_response = requests.get(f"{server_url}/health", timeout=5)
            if health_response.status_code != 200:
                raise Exception(f"IndexTTS server not available: {health_response.status_code}")
            print(f"✅ IndexTTS server available at {server_url}")
            
            # Update progress
            update_progress(50)
            
            # Prepare voice sample file path
            voice_sample_name = voice_sample or 'Male_town.wav'
            voice_sample_path = os.path.join('./api/VoiceSample', voice_sample_name)
            if not os.path.exists(voice_sample_path):
                raise Exception(f"Voice sample not found: {voice_sample_path}")
            print(f"🎵 Voice sample found: {voice_sample_path}")
            
            # Update progress
            update_progress(70)
            
            # Convert vPrompt emotion parameters to IndexTTS emotion vector format
            # IndexTTS expects: [anger, disgust, fear, happiness, neutral, sadness, surprise, other]
            emotion_vector = [
                emotion_params.get('angry', 0.0),      # Index 0: Anger
                emotion_params.get('disgust', 0.0),    # Index 1: Disgust
                emotion_params.get('afraid', 0.0),     # Index 2: Fear
                emotion_params.get('happy', 0.0),      # Index 3: Happiness
                emotion_params.get('calm', 0.5),       # Index 4: Neutral (using calm as neutral)
                emotion_params.get('sad', 0.0) + emotion_params.get('melancholic', 0.0),  # Index 5: Sadness (combine sad + melancholic)
                emotion_params.get('surprised', 0.0),  # Index 6: Surprise
                0.0                                     # Index 7: Other (not used)
            ]
            
            # Normalize emotion vector to ensure values are between 0.0 and 1.0
            emotion_vector = [max(0.0, min(1.0, val)) for val in emotion_vector]
            emotion_vector_str = f"[{','.join(map(str, emotion_vector))}]"
            
            print(f"🎭 Converted emotion vector: {emotion_vector_str}")
            print(f"🎭 Original emotion params: {emotion_params}")
            
            # Make request to FastAPI server using IndexTTS emotion vector format
            print(f"🚀 Sending request to FastAPI server with emotion vector...")
            with open(voice_sample_path, 'rb') as audio_file:
                files = {'reference_audio': audio_file}
                
                data = {
                    'text': cleaned_text,
                    'emo_vector': emotion_vector_str,
                    'emo_alpha': 1.0,  # Full emotion influence
                    'speed': 1.0,
                    'temperature': 0.7,
                    'top_k': 20,
                    'top_p': 0.8,
                    'repetition_penalty': 1.1
                }
                
                # Add emotion description if provided (for text-based emotion analysis)
                emotion_description = emotion_params.get('emotion_description', '').strip()
                if emotion_description:
                    data['use_emo_text'] = True
                    data['emo_text'] = emotion_description
                
                print(f"🎭 Sending IndexTTS data: {data}")
                response = requests.post(f"{server_url}/generate", files=files, data=data, timeout=120)
            
            if response.status_code == 200:
                # Generate unique filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_id = str(uuid.uuid4())[:8]
                local_filename = f"indextts_voice_{timestamp}_{unique_id}.wav"
                os.makedirs(GENERATED_FOLDER, exist_ok=True)
                local_path = os.path.join(GENERATED_FOLDER, local_filename)
                
                # Save the audio file
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                # Update progress
                update_progress(100)
                
                print(f"✅ IndexTTS voice generation completed: {local_path}")
                print(f"📁 File size: {len(response.content)} bytes")
                audio_files = [local_path]
            else:
                raise Exception(f"FastAPI request failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Error in voice generation: {e}")
            audio_files = None
        
        print(f"🎵 Job {job_id} IndexTTS voice generation completed, result: {audio_files}")
        
        # Process results
        with generation_jobs_lock:
            if audio_files:
                # Convert file paths to URLs
                audio_urls = []
                for audio_file in audio_files:
                    filename = os.path.basename(audio_file)
                    audio_urls.append({
                        'filename': filename,
                        'url': f'/uploads/generated/{filename}'
                    })
                
                generation_jobs[job_id]['progress'] = 100
                generation_jobs[job_id]['status'] = 'done'
                generation_jobs[job_id]['audio_files'] = audio_urls
                print(f"🎵 Job {job_id} voice generation completed successfully with {len(audio_urls)} audio files")
            else:
                generation_jobs[job_id]['status'] = 'error'
                generation_jobs[job_id]['error'] = 'IndexTTS voice generation failed - no audio files returned'
                print(f"⚠️ Job {job_id}: No audio files returned from IndexTTS voice generation")
                
    except Exception as e:
        logger.exception("Unhandled error in background_voice_generate for job %s: %s", job_id, e)
        with generation_jobs_lock:
            if job_id in generation_jobs:
                generation_jobs[job_id]['status'] = 'error'
                generation_jobs[job_id]['error'] = str(e)

def _background_generate(job_id, prompt_json, seed=None, modified_text=None):
    """Background worker that runs image generation without progress tracking."""
    logger = logging.getLogger(__name__)
    logger.info("Background generate started for job %s", job_id)

    try:
        # Set initial status to processing
        with generation_jobs_lock:
            generation_jobs[job_id]['status'] = 'processing'
            generation_jobs[job_id]['progress'] = 0

        # If modified text is provided, update the prompt in the JSON
        if modified_text:
            logger.info("Job %s: Using modified text from user input", job_id)
            # Find and update the text prompt in the JSON structure
            # This assumes the text prompt is in a node with class_type "CLIPTextEncode"
            for node_id, node_data in prompt_json.items():
                if isinstance(node_data, dict) and node_data.get('class_type') == 'CLIPTextEncode':
                    if 'inputs' in node_data and 'text' in node_data['inputs']:
                        logger.info("Job %s: Updating text prompt from '%s' to '%s'", job_id, 
                                  node_data['inputs']['text'][:50] + '...' if len(node_data['inputs']['text']) > 50 else node_data['inputs']['text'],
                                  modified_text[:50] + '...' if len(modified_text) > 50 else modified_text)
                        node_data['inputs']['text'] = modified_text
                        break

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
                        logger.info("🎯 PROGRESS CALLBACK CALLED: Job %s, Progress: %d%%", job_id, progress_percent)
                        with generation_jobs_lock:
                            if job_id in generation_jobs:
                                old_progress = generation_jobs[job_id].get('progress', 0)
                                generation_jobs[job_id]['progress'] = progress_percent
                                logger.info("📊 Job %s progress updated: %d%% → %d%%", job_id, old_progress, progress_percent)
                            else:
                                logger.warning("⚠️ Job %s not found in generation_jobs during progress update", job_id)
                    except Exception as e:
                        logger.error("❌ Failed to update progress for job %s: %s", job_id, e)
                
                logger.info("🚀 Job %s: Progress callback defined, calling generate_from_vprompt_dict", job_id)
                
                # Get ComfyUI server configuration
                server_address = os.getenv('COMFYUI_SERVER_ADDRESS', '127.0.0.1')
                server_port = os.getenv('COMFYUI_SERVER_PORT', '8188')
                
                generated_paths = generate_from_vprompt_dict(
                    prompt_json,
                    output_dir=GENERATED_FOLDER,
                    seed=seed,
                    progress_callback=update_progress,
                    server_address=server_address,
                    port=server_port
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

        # Get optional modified text parameter
        modified_text = None
        if request.is_json:
            json_data_req = request.get_json(silent=True)
            if json_data_req and 'modified_text' in json_data_req:
                modified_text = json_data_req.get('modified_text')
        else:
            modified_text = request.form.get('modified_text')

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
                'prompt_json': json_data,  # Store prompt for debug/log
                'modified_text': modified_text  # Store modified text
            }

        # Start background generation thread
        thread = threading.Thread(target=_background_generate, args=(job_id, json_data, seed, modified_text))
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
        'type': job.get('type', 'image')  # Default to image for backward compatibility
    }
    
    # Handle different job types
    if job.get('type') == 'voice':
        # Voice generation job
        if job['status'] == 'done':
            resp_dict['audio_files'] = job.get('audio_files', [])
    else:
        # Image generation job (default)
        resp_dict['prompt_json'] = job.get('prompt_json')
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

    # Return HTML response for frontend
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

@app.route('/upload_voice_sample', methods=['POST'])
def upload_voice_sample():
    """Handle voice sample file uploads for IndexTTS"""
    try:
        import tempfile
        import shutil
        from pydub import AudioSegment
        import uuid
        
        # Check if file was uploaded
        if 'voice_file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['voice_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file extension
        allowed_extensions = {'.wav', '.mp3', '.flac', '.m4a', '.ogg'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'Unsupported file format. Allowed: {list(allowed_extensions)}'}), 400
        
        # Check file size (max 50MB)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            return jsonify({'error': 'File too large. Maximum size: 50MB'}), 400
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Load and validate audio file
            audio = AudioSegment.from_file(temp_path)
            
            # Check duration (min 1 second, max 60 seconds)
            duration_seconds = len(audio) / 1000.0
            if duration_seconds < 1:
                return jsonify({'error': 'Audio too short. Minimum: 1 second'}), 400
            if duration_seconds > 60:
                return jsonify({'error': 'Audio too long. Maximum: 60 seconds'}), 400
            
            # Convert to required format (16-bit PCM WAV, 24kHz)
            audio = audio.set_frame_rate(24000).set_channels(1).set_sample_width(2)
            
            # Generate unique filename
            unique_id = str(uuid.uuid4())[:8]
            safe_filename = f"uploaded_{unique_id}.wav"
            output_path = os.path.join('./api/VoiceSample', safe_filename)
            
            # Save processed audio
            audio.export(output_path, format="wav")
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            return jsonify({
                'success': True,
                'filename': safe_filename,
                'duration': round(duration_seconds, 2),
                'file_url': f'/api/VoiceSample/{safe_filename}',
                'message': 'Voice sample uploaded successfully'
            })
            
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return jsonify({'error': f'Audio processing failed: {str(e)}'}), 400
            
    except ImportError:
        return jsonify({'error': 'Audio processing libraries not installed. Please install pydub.'}), 500
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/list_voice_samples', methods=['GET'])
def list_voice_samples():
    """List available voice samples from ./api/VoiceSample directory"""
    try:
        voice_sample_dir = './api/VoiceSample'
        voice_samples = []
        
        if os.path.exists(voice_sample_dir):
            for filename in sorted(os.listdir(voice_sample_dir)):
                if filename.endswith(('.wav', '.mp3', '.flac', '.m4a')):
                    # Create display name from filename
                    display_name = filename.replace('_', ' ').replace('.wav', '').replace('.mp3', '').replace('.flac', '').replace('.m4a', '')
                    voice_samples.append({
                        'filename': filename,
                        'display_name': display_name
                    })
        
        return jsonify({
            'voice_samples': voice_samples,
            'count': len(voice_samples)
        }), 200
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Error listing voice samples")
        return jsonify({"error": str(e)}), 500

@app.route('/start_voice_generation', methods=['POST'])
def start_voice_generation():
    """Start voice generation from text using job-based progress tracking"""
    try:
        # Get text, voice_sample, and emotion parameters from request - handle both JSON and FormData
        text = None
        voice_sample = None
        emotion_params = {}
        
        if request.is_json:
            data = request.get_json()
            text = data.get('text') if data else None
            voice_sample = data.get('voice_sample') if data else None
            # Extract emotion parameters
            emotion_params = {
                'emotion_description': data.get('emotion_description', '') if data else '',
                'angry': float(data.get('angry', 0)) if data and data.get('angry') is not None else 0.0,
                'sad': float(data.get('sad', 0)) if data and data.get('sad') is not None else 0.0,
                'happy': float(data.get('happy', 0)) if data and data.get('happy') is not None else 0.0,
                'afraid': float(data.get('afraid', 0)) if data and data.get('afraid') is not None else 0.0,
                'disgust': float(data.get('disgust', 0)) if data and data.get('disgust') is not None else 0.0,
                'melancholic': float(data.get('melancholic', 0)) if data and data.get('melancholic') is not None else 0.0,
                'surprised': float(data.get('surprised', 0)) if data and data.get('surprised') is not None else 0.0,
                'calm': float(data.get('calm', 0.5)) if data and data.get('calm') is not None else 0.5
            }
        else:
            text = request.form.get('text')
            voice_sample = request.form.get('voice_sample')
            # Extract emotion parameters from form data
            emotion_params = {
                'emotion_description': request.form.get('emotion_description', ''),
                'angry': float(request.form.get('angry', 0)),
                'sad': float(request.form.get('sad', 0)),
                'happy': float(request.form.get('happy', 0)),
                'afraid': float(request.form.get('afraid', 0)),
                'disgust': float(request.form.get('disgust', 0)),
                'melancholic': float(request.form.get('melancholic', 0)),
                'surprised': float(request.form.get('surprised', 0)),
                'calm': float(request.form.get('calm', 0.5))
            }
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
            
        if not voice_sample:
            return jsonify({"error": "No voice sample provided"}), 400
        
        # Log emotion parameters for debugging
        print(f"🎭 Voice generation with emotions: {emotion_params}")
        
        # Generate a unique job ID for the voice generation request
        job_id = str(uuid.uuid4())
        
        # Initialize the job in the global jobs dictionary
        with generation_jobs_lock:
            generation_jobs[job_id] = {
                'status': 'pending',
                'progress': 0,
                'audio_files': [],
                'error': None,
                'type': 'voice'  # Mark this as a voice generation job
            }
        
        # Start background voice generation thread with emotion parameters
        thread = threading.Thread(target=_background_voice_generate, args=(job_id, text, voice_sample, emotion_params))
        thread.daemon = True
        thread.start()
        
        # Return job ID for frontend to poll
        return jsonify({
            'job_id': job_id,
            'message': 'Voice generation started',
            'status': 'pending'
        }), 200
            
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Error in start_voice_generation")
        return jsonify({"error": str(e)}), 500


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

@app.route('/indextts_demo.html')
def indextts_demo():
    return send_from_directory('.', 'indextts_demo.html')

@app.route('/test_voice_functionality.html')
def test_voice_functionality():
    return send_from_directory('.', 'test_voice_functionality.html')

@app.route('/api/VoiceSample/<filename>')
def voice_sample(filename):
    return send_from_directory('./api/VoiceSample', filename)

@app.route('/test_voice_output/<filename>')
def test_voice_output(filename):
    return send_from_directory('./test_voice_output', filename)

@app.route('/api/voice_samples')
def get_voice_samples():
    """Return list of available voice samples"""
    import os
    voice_samples_dir = './api/VoiceSample'
    try:
        files = [f for f in os.listdir(voice_samples_dir) if f.endswith('.wav')]
        files.sort()  # Sort alphabetically
        return jsonify({
            'success': True,
            'voice_samples': files
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def handle_fastapi_indextts(server_url, server_name, text, audio_file_path, request):
    """Handle IndexTTS FastAPI endpoint calls"""
    import requests
    import uuid
    import shutil
    from datetime import datetime
    
    try:
        # Get parameters from form data
        speed = float(request.form.get('speed', 1.0))
        temperature = float(request.form.get('temperature', 0.7))
        top_k = int(request.form.get('topK', 20))
        top_p = float(request.form.get('topP', 0.8))
        repetition_penalty = float(request.form.get('repetitionPenalty', 1.1))
        
        # Prepare the request to FastAPI endpoint
        files = {
            'reference_audio': open(audio_file_path, 'rb')
        }
        
        data = {
            'text': text,
            'speed': speed,
            'temperature': temperature,
            'top_k': top_k,
            'top_p': top_p,
            'repetition_penalty': repetition_penalty
        }
        
        # Make request to FastAPI endpoint
        response = requests.post(f"{server_url}/generate", files=files, data=data, timeout=120)
        
        # Close the file
        files['reference_audio'].close()
        
        if response.status_code != 200:
            return jsonify({
                'error': f'FastAPI IndexTTS request failed with status {response.status_code}',
                'details': response.text,
                'suggestion': 'Check the server logs for more details.'
            }), response.status_code
        
        # Handle the response - FastAPI returns binary audio data directly
        content_type = response.headers.get('content-type', '')
        
        if 'audio' in content_type.lower():
            # Server returns binary audio data directly
            # Generate local filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            local_filename = f"vPrompt_voice_{timestamp}_{unique_id}.wav"
            local_path = os.path.join('./test_voice_output', local_filename)
            
            # Ensure output directory exists
            os.makedirs('./test_voice_output', exist_ok=True)
            
            # Save the audio file directly from response content
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            # Extract generation info from headers if available
            permanent_filename = response.headers.get('x-permanent-filename', 'N/A')
            
            return jsonify({
                'success': True,
                'message': f'Voice generated successfully using {server_name} FastAPI',
                'audio_file': local_filename,
                'audio_url': f'/test_voice_output/{local_filename}',
                'server_used': server_name,
                'generation_time': 'N/A',
                'original_filename': permanent_filename
            })
        else:
            # Try to parse as JSON (fallback for different API versions)
            try:
                result = response.json()
                if 'audio_url' in result:
                    # Download the generated audio file
                    audio_response = requests.get(result['audio_url'])
                    if audio_response.status_code == 200:
                        # Generate local filename
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_id = str(uuid.uuid4())[:8]
                        local_filename = f"vPrompt_voice_{timestamp}_{unique_id}.wav"
                        local_path = os.path.join('./test_voice_output', local_filename)
                        
                        # Ensure output directory exists
                        os.makedirs('./test_voice_output', exist_ok=True)
                        
                        # Save the audio file
                        with open(local_path, 'wb') as f:
                            f.write(audio_response.content)
                        
                        return jsonify({
                            'success': True,
                            'message': f'Voice generated successfully using {server_name} FastAPI',
                            'audio_file': local_filename,
                            'audio_url': f'/test_voice_output/{local_filename}',
                            'server_used': server_name,
                            'generation_time': result.get('generation_time', 'N/A')
                        })
                    else:
                        return jsonify({
                            'error': 'Failed to download generated audio file',
                            'suggestion': 'The audio was generated but could not be retrieved.'
                        }), 500
                else:
                    return jsonify({
                        'error': 'No audio URL in FastAPI response',
                        'response': result,
                        'suggestion': 'Check the FastAPI server implementation.'
                    }), 500
            except ValueError as json_error:
                return jsonify({
                    'error': f'FastAPI IndexTTS request failed: Invalid response format',
                    'details': f'Expected audio data or JSON, got: {content_type}',
                    'suggestion': 'Check the FastAPI server implementation and response format.'
                }), 500
            
    except requests.exceptions.Timeout:
        return jsonify({
            'error': 'Request timeout to FastAPI IndexTTS server',
            'suggestion': 'The server may be overloaded. Please try again later.'
        }), 504
    except Exception as e:
        return jsonify({
            'error': f'FastAPI IndexTTS request failed: {str(e)}',
            'suggestion': 'Check the server status and try again.'
        }), 500

@app.route('/check_indextts_servers', methods=['GET'])
def check_indextts_servers():
    """Check the status of available IndexTTS servers"""
    import requests
    
    # IndexTTS server configuration
    INDEXTTS_SERVERS = [
        {"url": "http://192.168.68.30:8000", "name": "FastAPI", "type": "fastapi"},
        {"url": "http://192.168.68.30:7860", "name": "Gradio", "type": "gradio"}
    ]
    
    server_status = {}
    
    for server in INDEXTTS_SERVERS:
        try:
            # Use different health check endpoints for different server types
            if server['type'] == 'fastapi':
                health_endpoint = f"{server['url']}/health"
            else:
                health_endpoint = f"{server['url']}/config"
            
            response = requests.get(health_endpoint, timeout=5)
            if response.status_code == 200:
                server_status[server['type']] = {
                    'available': True,
                    'url': server['url'],
                    'name': server['name'],
                    'status': 'online'
                }
            else:
                server_status[server['type']] = {
                    'available': False,
                    'url': server['url'],
                    'name': server['name'],
                    'status': f'error_{response.status_code}'
                }
        except Exception as e:
            server_status[server['type']] = {
                'available': False,
                'url': server['url'],
                'name': server['name'],
                'status': f'offline: {str(e)}'
            }
    
    return jsonify(server_status)

@app.route('/indextts_upload_test.html')
def indextts_upload_test():
    return send_from_directory('.', 'indextts_upload_test.html')

@app.route('/generate_indextts', methods=['POST'])
def generate_indextts():
    """Handle IndexTTS API calls and save generated files locally"""
    audio_file_path = None
    is_temp_file = False
    
    try:
        from gradio_client import Client
        import shutil
        import uuid
        from datetime import datetime
        import requests
        
        # Get form data
        text = request.form.get('text', '').strip()
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        # Handle audio file upload or voice sample selection
        audio_file_path = None
        
        # Check if an audio file was uploaded
        if 'audio_file' in request.files:
            audio_file = request.files['audio_file']
            if audio_file.filename != '':
                # Save uploaded file temporarily
                filename = secure_filename(audio_file.filename)
                temp_filename = f"temp_{uuid.uuid4().hex}_{filename}"
                audio_file_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
                
                # Ensure upload directory exists
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                audio_file.save(audio_file_path)
        
        # Fallback to voice sample selection if no file uploaded
        if not audio_file_path:
            voice_sample = request.form.get('voice_sample', '').strip()
            if not voice_sample:
                return jsonify({'error': 'Either upload an audio file or select a voice sample'}), 400
                
            # Construct path to selected voice sample
            audio_file_path = os.path.join('./api/VoiceSample', voice_sample)
        
        # Verify the audio file exists
        if not os.path.exists(audio_file_path):
            return jsonify({'error': f'Audio file not found: {audio_file_path}'}), 400
        
        # Track if we need to clean up temporary file
        is_temp_file = 'temp_' in os.path.basename(audio_file_path)
        
        # IndexTTS server configuration (remote only due to resource constraints)
        INDEXTTS_SERVERS = [
            {"url": "http://192.168.68.30:8000", "name": "remote_api", "type": "fastapi", "verbose_errors": True},
            {"url": "http://192.168.68.30:7860", "name": "remote_gradio", "type": "gradio", "verbose_errors": False}
        ]
        
        # Check if user specified a server type
        preferred_server_type = request.form.get('server_type', '').strip()
        
        def get_available_indextts_server():
            """Find the first available IndexTTS server, preferring user selection"""
            # If user specified a server type, try that first
            if preferred_server_type:
                for server in INDEXTTS_SERVERS:
                    if server['type'] == preferred_server_type:
                        try:
                            # Use different health check endpoints for different server types
                            if server['type'] == 'fastapi':
                                health_endpoint = f"{server['url']}/health"
                            else:
                                health_endpoint = f"{server['url']}/config"
                            
                            response = requests.get(health_endpoint, timeout=5)
                            if response.status_code == 200:
                                print(f"✅ Using preferred server: {server['name']} at {server['url']}")
                                return server
                        except Exception as e:
                            print(f"❌ Preferred server {server['name']} at {server['url']} is not available: {e}")
                            continue
            
            # Fallback to any available server
            for server in INDEXTTS_SERVERS:
                try:
                    # Use different health check endpoints for different server types
                    if server['type'] == 'fastapi':
                        health_endpoint = f"{server['url']}/health"
                    else:
                        health_endpoint = f"{server['url']}/config"
                    
                    response = requests.get(health_endpoint, timeout=5)
                    if response.status_code == 200:
                        print(f"✅ IndexTTS server '{server['name']}' is available at {server['url']}")
                        return server
                except Exception as e:
                    print(f"❌ IndexTTS server '{server['name']}' at {server['url']} is not available: {e}")
                    continue
            return None
        
        # Find available IndexTTS server
        server_config = get_available_indextts_server()
        if not server_config:
            return jsonify({
                'error': 'IndexTTS server is not available',
                'suggestion': 'Please contact the server administrator to ensure the IndexTTS server is running and accessible',
                'technical_details': 'Remote server at 192.168.68.30 is not responding'
            }), 503
        
        server_url = server_config['url']
        server_name = server_config['name']
        server_type = server_config['type']
        print(f"Using IndexTTS server: {server_name} at {server_url}")
        
        # Check if this is the FastAPI endpoint
        if server_type == 'fastapi':
            return handle_fastapi_indextts(server_url, server_name, text, audio_file_path, request)
        
        # Handle Gradio endpoint (port 7860)
        # Server connectivity already verified in get_available_indextts_server()
        
        # Connect to IndexTTS server
        try:
            client = Client(server_url)
        except Exception as e:
            return jsonify({
                'error': f'Failed to initialize IndexTTS client for {server_name} server: {str(e)}',
                'suggestion': 'The IndexTTS server may be overloaded or misconfigured. Please wait a moment and try again.',
                'technical_details': f'Client initialization error for {server_url}'
            }), 503
        
        # Get emotion and generation parameters from form data
        emotion_description = request.form.get('emotionDescription', '')
        angry = float(request.form.get('angry', 0.0))
        sad = float(request.form.get('sad', 0.0))
        happy = float(request.form.get('happy', 0.0))
        afraid = float(request.form.get('afraid', 0.0))
        disgust = float(request.form.get('disgust', 0.0))
        melancholic = float(request.form.get('melancholic', 0.0))
        surprised = float(request.form.get('surprised', 0.0))
        calm = float(request.form.get('calm', 0.5))
        temperature = float(request.form.get('temperature', 0.7))
        top_k = int(request.form.get('topK', 50))
        top_p = float(request.form.get('topP', 0.8))
        length_penalty = float(request.form.get('lengthPenalty', 1.0))
        num_beams = int(request.form.get('numBeams', 1))
        repetition_penalty = float(request.form.get('repetitionPenalty', 10.0))
        max_mel_tokens = int(request.form.get('maxMelTokens', 1500))
        
        # Prepare parameters in the exact order expected by the API (24 parameters)
        params = [
            None,                    # param_0: Form component
            None,                    # param_1: Column component  
            audio_file_path,         # param_2: Voice Reference (audio)
            text,                    # param_3: Text (textbox)
            None,                    # param_4: Column component
            None,                    # param_5: Row component
            angry,                   # param_6: Angry (slider, 0.0-1.0)
            sad,                     # param_7: Sad (slider, 0.0-1.0)
            happy,                   # param_8: Happy (slider, 0.0-1.0)
            afraid,                  # param_9: Afraid (slider, 0.0-1.0)
            disgust,                 # param_10: Disgust (slider, 0.0-1.0)
            melancholic,             # param_11: Melancholic (slider, 0.0-1.0)
            surprised,               # param_12: Surprised (slider, 0.0-1.0)
            calm,                    # param_13: Calm (slider, 0.0-1.0)
            None,                    # param_14: Column component
            None,                    # param_15: Upload emotion reference audio
            emotion_description,     # param_16: Emotion description (textbox)
            None,                    # param_17: Row component
            None,                    # param_18: Column component
            temperature,             # param_19: temperature (slider, 0.1-2.0)
            top_k,                   # param_20: top_k (slider, 1-100)
            top_p,                   # param_21: top_p (slider, 0.1-2.0)
            length_penalty,          # param_22: length_penalty (number)
            num_beams,               # param_23: num_beams (slider, 1-10)
            repetition_penalty,      # param_24: repetition_penalty (number)
            max_mel_tokens           # param_25: max_mel_tokens (slider, 50-1815)
        ]
        
        # Make API call with all parameters
        try:
            result = client.predict(*params, api_name="/gen_single")
        except Exception as api_error:
            error_msg = str(api_error)
            if "verbose error reporting" in error_msg.lower():
                return jsonify({
                    'error': 'IndexTTS server configuration issue',
                    'details': 'The server needs verbose error reporting enabled',
                    'suggestion': 'Contact the server administrator to add show_error=True in the Gradio launch configuration',
                    'technical_details': error_msg
                }), 500
            elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                return jsonify({
                    'error': 'Connection timeout to IndexTTS server',
                    'suggestion': 'The server may be overloaded. Please try again in a few moments.',
                    'technical_details': error_msg
                }), 503
            else:
                return jsonify({
                    'error': 'IndexTTS API call failed',
                    'suggestion': 'Please check your input parameters and try again.',
                    'technical_details': error_msg
                }), 500
        
        # Handle the result
        generated_file_path = None
        if isinstance(result, str) and (result.endswith('.wav') or result.endswith('.mp3') or result.endswith('.flac')):
            generated_file_path = result
        elif isinstance(result, (list, tuple)):
            for item in result:
                if isinstance(item, str) and (item.endswith('.wav') or item.endswith('.mp3') or item.endswith('.flac')):
                    generated_file_path = item
                    break
                    
        if not generated_file_path:
            return jsonify({
                'error': 'No audio file path returned from IndexTTS',
                'suggestion': 'The generation may have failed silently. Check IndexTTS server logs.',
                'result_received': str(result)[:200] + '...' if len(str(result)) > 200 else str(result)
            }), 500
            
        if not os.path.exists(generated_file_path):
            return jsonify({
                'error': 'Generated audio file not found on server',
                'suggestion': 'The file may have been generated but not saved properly.',
                'expected_path': generated_file_path
            }), 500
            
        # Generate local filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(generated_file_path)[1]
        local_filename = f"indextts_generated_{timestamp}_{uuid.uuid4().hex[:8]}{file_extension}"
        local_file_path = os.path.join(GENERATED_FOLDER, local_filename)
        
        # Copy generated file to local storage
        shutil.copy2(generated_file_path, local_file_path)
            
        # Get file info
        file_size = os.path.getsize(local_file_path)
        
        return jsonify({
            'success': True,
            'message': 'Audio generated successfully',
            'filename': local_filename,
            'file_path': local_file_path,
            'file_size': file_size,
            'download_url': f'/uploads/generated/{local_filename}',
            'text': text
        })
        
    except ImportError:
        return jsonify({'error': 'gradio_client not installed. Run: pip install gradio_client'}), 500
    except Exception as e:
        return jsonify({'error': f'Generation failed: {str(e)}'}), 500
    finally:
        # Clean up temporary files
        if is_temp_file and audio_file_path and os.path.exists(audio_file_path):
            try:
                os.remove(audio_file_path)
                print(f"🗑️ Cleaned up temporary file: {audio_file_path}")
            except Exception as cleanup_error:
                print(f"⚠️ Failed to clean up temporary file {audio_file_path}: {cleanup_error}")

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
