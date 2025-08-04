# vPrompt

## 功能簡介
本專案是一個 Web 應用，讓用戶上傳圖片，選擇場景、主角、時間等，並用 Gemini 2.0 Flash API 生成創意的 Image/Video Prompt。支援多國語言輸出，Prompt 以文本和 JSON 顯示，並提供下載和複製功能。

## 主要功能
- 🖼️ 圖片上傳與智能識別
- 🎬 選擇提示類型（圖片/影片）
- 🌍 多語言支援（英語、繁體中文、簡體中文、日語、韓語、法語、德語、西班牙語）
- ⏰ 時間選擇
- 🏞️ 場景設定（戶外、室內、自定義）
- 👤 主角選擇（包含情侶、攝影師等多種角色）
- 📝 額外描述欄位（支援運鏡、角度等專業術語）
- 🤖 AI 圖片識別與 Prompt 增強
- 📄 Prompt 以文本和 JSON 格式顯示
- 📥 下載 Prompt 文件
- 📋 一鍵複製功能
- 💾 表單狀態記憶（使用 Cookie）

## 環境需求
- Python 3.8+
- Google Gemini API Key

## 安裝步驟

### 1. 克隆專案
```bash
git clone https://github.com/elbartohub/vprompt.git
cd vPrompt
```

### 2. 建立 Python 虛擬環境
```bash
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. 安裝相依套件
```bash
pip install -r requirements.txt
```

### 4. 環境變數設定
```bash
# 複製環境變數範例檔案
cp .env.example .env

# 編輯 .env 檔案，填入你的 API Key
nano .env
```

在 `.env` 檔案中設定：
```env
GEMINI_API_KEY=your_google_gemini_api_key_here
```

### 5. 啟動應用程式
```bash
python app.py
```

應用程式將在 http://localhost:5001 啟動。

## API 設定

### Gemini API Key 取得
1. 前往 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 點擊「Create API Key」
3. 複製 API Key 並設定到 `.env` 檔案中

### Google Drive API 設定（可選）
1. 前往 [Google Cloud Console](https://console.cloud.google.com/) 建立 OAuth 2.0 憑證
2. 下載 `credentials.json` 放在專案根目錄
3. 首次分享時會要求授權

## 使用說明

### 基本使用流程
1. **選擇提示類型**：圖片或影片
2. **選擇輸出語言**：支援 8 種語言
3. **上傳圖片**（可選）：系統會自動識別圖片內容
4. **設定參數**：
   - 時間：影響光線和氛圍
   - 場景：戶外、室內或自定義
   - 主角：多種角色選擇
   - 額外描述：加入運鏡、角度等專業描述
5. **生成 Prompt**：點擊生成按鈕
6. **查看結果**：文本和 JSON 格式
7. **下載或複製**：方便後續使用

### 無圖片模式
即使不上傳圖片，系統也能根據您的設定生成豐富的 Prompt：
- 系統會根據場景、主角、時間等參數智能推斷
- Gemini AI 會自動補充合理的視覺描述
- 特別適合快速生成創意 Prompt

## 專案結構
```
vPrompt/
├── app.py                 # Flask 主應用程式
├── templates/
│   └── index.html         # 主頁面模板
├── static/
│   ├── style.css          # 樣式檔案
│   └── script.js          # 前端 JavaScript
├── uploads/               # 圖片上傳目錄
├── requirements.txt       # Python 套件清單
├── .env.example          # 環境變數範例
├── .gitignore            # Git 忽略檔案
└── README.md             # 說明文件
```

## 技術特點
- **後端**：Flask + Gemini 2.0 Flash API
- **前端**：HTML5 + CSS3 + JavaScript (ES6+)
- **AI 整合**：Google Gemini 2.0 Flash 模型
- **多語言**：支援 8 種語言輸出
- **響應式設計**：支援桌面和行動裝置
- **狀態保持**：使用 Cookie 記住用戶偏好

## 疑難排解

### 常見問題
1. **API Key 錯誤**
   - 確認 `.env` 檔案中的 `GEMINI_API_KEY` 設定正確
   - 檢查 API Key 是否有效且有足夠額度

2. **圖片上傳失敗**
   - 確認圖片格式為 PNG、JPG、JPEG 或 GIF
   - 檢查 `uploads/` 目錄權限

3. **虛擬環境問題**
   - 確認已啟動虛擬環境
   - 重新安裝相依套件：`pip install -r requirements.txt`

## 授權
MIT License

## 貢獻
歡迎提交 Issue 和 Pull Request！
