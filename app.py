import os
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from werkzeug.utils import secure_filename
# 假設 Gemini API 有官方 Python SDK
# from gemini_flash_lite_sdk import GeminiClient
import requests
from dotenv import load_dotenv
import base64
from flask import make_response

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

load_dotenv()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    prompt_text = None
    prompt_json = None
    prompt_json_str = None
    image_url = None
    print("[DEBUG] Request method:", request.method)
    # 讀取 cookie 預設值
    prompt_type = request.cookies.get('prompt_type', 'image')
    output_lang = request.cookies.get('output_lang', 'en')
    # Handle zh-TW to zh-tw conversion for display consistency
    output_lang_display = 'zh-tw' if output_lang == 'zh-TW' else output_lang
    # 修正繁體中文選項，前端用 zh-tw，後端語言映射也需一致
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
    image_filename = request.cookies.get('image_filename', '')
    if image_filename:
        image_url = url_for('uploaded_file', filename=image_filename)
    else:
        image_url = None
    if request.method == 'POST':
        prompt_type = request.form.get('prompt_type')
        output_lang = request.form.get('output_lang', 'en')
        print(f"[DEBUG] Form data: prompt_type={prompt_type}, output_lang={output_lang}")
        # Store the original form value for display, but use converted value for API calls
        output_lang_display = output_lang
        # 修正 zh-tw 映射
        if output_lang == 'zh-tw':
            output_lang = 'zh-TW'
        time = request.form.get('time')
        scene = request.form.get('scene')
        custom_scene = request.form.get('custom_scene')
        character = request.form.get('character')
        custom_character = request.form.get('custom_character')
        extra_desc = request.form.get('extra_desc')
        file = request.files.get('image')
        image_path = None
        image_filename = ''
        print(f"[DEBUG] Form data: time={time}, scene={scene}, custom_scene={custom_scene}, character={character}, custom_character={custom_character}, extra_desc={extra_desc}, file={file.filename if file else None}")
        # Always set cookies for scene and character, even if value is '其它' or empty
        # 若所有欄位皆空，直接清空結果
        if not any([prompt_type, output_lang, time, scene, custom_scene, character, custom_character, extra_desc, file]):
            print("[DEBUG] All fields empty, clearing result.")
            prompt_json = None
            prompt_text = ''
            image_url = None
        else:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(image_path)
                image_url = url_for('uploaded_file', filename=filename)
                image_filename = filename
                print(f"[DEBUG] Image saved: {image_path}")
        # 圖片識別（Gemini 2.0 Flash HTTP API）
        if image_path:
            api_key = os.getenv('GEMINI_API_KEY', 'YOUR_API_KEY')
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
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
            prompt_text_recog = f"Please identify this image in detail and output as JSON: Scene, ambiance_or_mood, Location, Visual style, camera motion, lighting, ending. All responses must be in {prompt_lang}." if output_lang == 'en' else f"請詳細識別這張圖片，並以 json 格式輸出：Scene、ambiance_or_mood、Location、Visual style、camera motion、lighting、ending。所有回應內容一律使用{prompt_lang}。"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt_text_recog},
                            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
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
                    result = pyjson.loads(match.group())
                    print(f"[DEBUG] Parsed image recognition result: {result}")
                except Exception as e:
                    print(f"[DEBUG] JSON parse error: {e}")
                    result = None
            else:
                print("[DEBUG] No JSON found in Gemini response text.")
                result = None
            # 若 result 為 None，則用空欄位
            if not result:
                print("[DEBUG] Using empty fields for image recognition result.")
                result = {'Scene': '', 'ambiance_or_mood': '', 'Location': '', 'Visual style': '', 'camera motion': '', 'lighting': '', 'ending': ''}
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
                'camera motion': 'video' if prompt_type == 'video' else '',  # Set camera motion for video prompts
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
                
                # Ask Gemini to enhance the user inputs
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
                    enhance_prompt = f"Based on these user inputs: {user_input_text}, please create a detailed JSON with the following fields: Scene, ambiance_or_mood, Location, Visual style, camera motion, lighting, ending. Fill in creative and appropriate details for missing fields. Output in {prompt_lang} and format as valid JSON only."
                else:
                    enhance_prompt = f"根據這些用戶輸入: {user_input_text}，請創建一個詳細的 JSON，包含以下欄位：Scene、ambiance_or_mood、Location、Visual style、camera motion、lighting、ending。為缺少的欄位填入富有創意且合適的細節。請用{prompt_lang}回應，並只輸出有效的 JSON 格式。"
                
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
                                # Use enhanced result if parsing successful
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
        # 整合用戶選擇
        main_character = character if character != '其它' else custom_character
        def skip_custom(val):
            return '' if val == '用戶自定' else val
        def infer_or_value(val, field_name):
            return val if val else ''
        prompt_json = {
            'Scene': infer_or_value(skip_custom(result['Scene']), 'Scene'),
            'ambiance_or_mood': infer_or_value(skip_custom(result['ambiance_or_mood']), 'ambiance_or_mood'),
            'Location': infer_or_value(skip_custom(result['Location']), 'Location'),
            'Visual style': infer_or_value(skip_custom(result['Visual style']), 'Visual style'),
            'camera motion': infer_or_value(skip_custom(result['camera motion']), 'camera motion'),
            'lighting': infer_or_value(skip_custom(result['lighting']), 'lighting'),
            'ending': infer_or_value(skip_custom(result['ending']), 'ending'),
            'type': infer_or_value(prompt_type, 'type'),
            'time': infer_or_value(time, 'time'),
            'main_character': infer_or_value(skip_custom(main_character), 'main_character'),
            'extra_desc': infer_or_value(extra_desc, 'extra_desc')
        }
        print(f"[DEBUG] prompt_json: {prompt_json}")
        # 交給 Gemini 重新組合 json 內容為一篇可讀性高的作品
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
            prompt_for_gemini = f"Please rewrite the following JSON content into a highly readable, natural, and fluent {prompt_lang} description, omitting all field titles and separators, and arranging the order logically: {json.dumps(prompt_json_for_gemini, ensure_ascii=False)}"
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
    # 僅在 prompt_json 有有效內容時才生成
    def is_all_infer_or_default(j):
        if not j:
            return True
        infer_keys = [
            'Scene', 'ambiance_or_mood', 'Location', 'Visual style', 'camera motion', 'lighting', 'ending', 'main_character', 'extra_desc'
        ]
        for k in infer_keys:
            v = j.get(k, '')
            if v and not v.startswith('[Please infer'):
                return False
        # type/image, time/00:00 可視為預設
        if j.get('type', '') != 'image':
            return False
        if j.get('time', '') != '00:00':
            return False
        return True

    valid_json = prompt_json and not is_all_infer_or_default(prompt_json)
    print(f"[DEBUG] valid_json: {valid_json}")
    # 只要 prompt_text 有內容就顯示，不再強制清空
    if valid_json:
        prompt_json_str = json.dumps(prompt_json, ensure_ascii=False, indent=2)
        print(f"[DEBUG] prompt_json_str: {prompt_json_str}")
    else:
        print("[DEBUG] No valid prompt_json, but keep prompt_text if present.")
        prompt_json_str = None
        # prompt_text 不清空，讓 UI 能顯示
    print(f"[DEBUG] Final prompt_text: {prompt_text}")
    # 設定 cookie
    resp = make_response(render_template('index.html', 
                                       prompt_text=prompt_text, 
                                       prompt_json=prompt_json, 
                                       prompt_json_str=prompt_json_str, 
                                       image_url=image_url,
                                       prompt_type=prompt_type,
                                       output_lang=output_lang_display,
                                       time=time,
                                       scene=scene,
                                       custom_scene=custom_scene,
                                       character=character,
                                       custom_character=custom_character,
                                       extra_desc=extra_desc))
    if request.method == 'POST':
        if prompt_type is not None:
            resp.set_cookie('prompt_type', prompt_type)
        if output_lang is not None:
            resp.set_cookie('output_lang', output_lang_display)
        if time is not None:
            resp.set_cookie('time', time)
        # Always set scene and character cookies, even if value is '其它' or empty
        resp.set_cookie('scene', scene if scene is not None else '')
        resp.set_cookie('custom_scene', custom_scene if custom_scene is not None else '')
        resp.set_cookie('character', character if character is not None else '')
        resp.set_cookie('custom_character', custom_character if custom_character is not None else '')
        resp.set_cookie('extra_desc', extra_desc if extra_desc is not None else '')
        # 不存 image_filename 於 cookies，避免跨 session 顯示已上傳圖片
    return resp

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

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

# Google Drive 分享功能略（需 OAuth 流程）

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, port=port)
