# vPrompt Generator - AI Prompt 生成器

## ✨ 最新更新 (v2.1.0 - 2025年8月)
- **🎨 Creative Mode**：全新創意模式，生成更具藝術性、實驗性和想像力的提示詞
- **⚛️ 反物理元素系統**：局部重力潮汐、時空變形、物質轉換等突破性視覺概念
- **🌀 變形系統**：液態金屬變形、粒子重組、能量形態轉換
- **📱 HEIC 支援**：完整支援 iPhone HEIC 格式照片
- **📱 響應式設計**：完美支援手機和平板裝置
- **🎬 增強運鏡**：Creative Mode 提供突破性的攝影機運動建議
- **🌟 視覺強化**：更豐富的視覺故事敘述和情感張力

![alt text](images/vprompt01.jpg)

### 🎨 Creative Mode 展示
![Creative Mode 界面展示](images/creative-mode-demo.jpg)
*Creative Mode 提供突破性的視覺創意生成功能*

## 主要功能
- 🖼️ **智能圖片識別**：AI 自動分析圖片內容和視覺元素
- 🎬 **提示類型選擇**：支援圖片和影片兩種 Prompt 生成模式
- 🎨 **Creative Mode**：創意模式生成更具藝術性、實驗性的視覺內容
- ⚛️ **反物理元素系統**：突破物理定律的視覺概念（重力操控、時空變形、物質轉換）
- 🌍 **多語言支援**：8 種語言輸出（英語、繁體中文、簡體中文、日語、韓語、法語、德語、西班牙語）
- ⏰ **時間選擇**：影響光線氛圍的時間設定
- 🏞️ **場景設定**：戶外、室內或自定義場景選擇
- 👤 **豐富角色選項**：包含情侶、攝影師、學生等多種主角類型
- 📝 **專業描述欄位**：支援運鏡、角度、風格等專業術語
- 🎯 **突破性運鏡**：Creative Mode 提供前衛的攝影機運動建議
- 🌀 **變形系統**：液態金屬變形、粒子重組、能量轉換等視覺效果
- 🤖 **AI 增強模式**：無圖片時智能生成豐富的視覺描述
- 📄 **雙格式輸出**：文本和結構化 JSON 格式
- 📥 **便捷下載**：一鍵下載生成的 Prompt 文件
- 📋 **快速複製**：一鍵複製功能，支援剪貼板操作


## 環境需求
- Python 3.12
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

#### 🌐 網路存取設定
預設情況下，應用程式支援網路存取（`HOST=0.0.0.0`）：
- **本機存取**: http://localhost:5001
- **網路存取**: http://[your-ip-address]:5001

若要僅限本機存取，可在 `.env` 檔案中設定：
```env
HOST=127.0.0.1
PORT=5001
FLASK_DEBUG=True
```

## API 設定

### Gemini API Key 取得
1. 前往 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 點擊「Create API Key」
3. 複製 API Key 並設定到 `.env` 檔案中

### Google Drive API 設定（可選）
1. 前往 [Google Cloud Console](https://console.cloud.google.com/) 建立 OAuth 2.0 憑證
2. 下載 `credentials.json` 放在專案根目錄
3. 首次分享時會要求授權

### Creative Mode 技術實現
Creative Mode 透過進階的提示詞工程技術實現：

#### 🔧 後端實現
```python
# Creative Mode 反物理元素增強提示詞
if creative_mode:
    prompt = f"""
    CREATIVE MODE: Be highly creative, artistic, and experimental.
    
    ANTI-PHYSICS ELEMENTS to incorporate:
    - Localized Gravitational Tides: Objects affected by warped gravity fields
    - Transformation Systems: Matter state changes (liquid metal, particle reconstruction)
    - Temporal Distortions: Time dilation zones, chronological anomalies
    - Spatial Anomalies: Non-Euclidean geometry, dimensional rifts
    - Elemental Violations: Water flowing upward, geometric fire patterns
    - Light Manipulation: Solidified light beams, photon sculptures
    
    CAMERA MOTION with anti-physics:
    - 'Gravity-defying orbital tracking through time-dilated space'
    - 'Liquid mercury camera flow morphing through dimensional barriers'
    - 'Particle-dissolution perspective shifts in gravitational tides'
    - 'Quantum tunnel cinematography through folded reality'
    
    Make it visually stunning, emotionally powerful, and scientifically impossible.
    """
```

#### 前端實現
```javascript
// Creative Mode 狀態管理
document.getElementById('creativeMode').addEventListener('change', function() {
    const isCreative = this.checked;
    document.cookie = `creative_mode=${isCreative}; path=/; max-age=31536000`;
});
```

## 使用說明

### 基本使用流程
1. **選擇提示類型**：圖片或影片 Prompt 生成模式
2. **選擇輸出語言**：支援 8 種國際語言
3. **🎨 Creative Mode**：啟用創意模式獲得更具藝術性的輸出
4. **圖片上傳**（可選）：
   - **拖放上傳**：直接將圖片拖拽到上傳區域
   - **點擊選擇**：點擊上傳區域瀏覽文件
   - **即時預覽**：上傳後立即顯示圖片預覽和文件信息
   - **輕鬆移除**：點擊 × 按鈕移除已選圖片
5. **參數設定**：
   - **時間選擇**：影響光線氛圍和視覺效果
   - **場景設定**：戶外、室內或自定義環境
   - **主角選擇**：豐富的角色類型（情侶、攝影師、學生等）
   - **專業描述**：運鏡技巧、拍攝角度、視覺風格等
6. **生成 Prompt**：點擊生成按鈕，AI 開始處理
7. **查看結果**：雙格式輸出（自然語言文本 + 結構化 JSON）
8. **快速操作**：一鍵複製或下載生成的 Prompt

### 🎨 Creative Mode 功能
Creative Mode 是 vPrompt 的核心創新功能，為創作者提供突破性的視覺內容生成：

#### 🎬 前衛運鏡系統
突破傳統攝影機運動的創新建議：
- **超現實螺旋下降環繞主體**
- **時間擴張追蹤穿越虛幻空間**
- **無重力軌道拍攝**
- **夢境般變形透視**
- **萬花筒旋轉序列**
- **詩意流動轉場**

#### ⚛️ 反物理元素系統
Creative Mode 引入突破物理定律的視覺概念：

**🌌 重力操控效果**
- **局部重力潮汐 (Localized Gravitational Tides)**：物體在特定區域受到扭曲重力影響
- **重力反轉領域**：人物或物體在重力倒置的空間中漂浮
- **重力波紋**：重力如水波般擴散，影響周圍物體的運動軌跡
- **微重力氣泡**：創造局部無重力環境，物體自由漂浮

**🔄 時空變形效果**
- **時間膨脹區域**：局部時間流速改變，創造慢動作或快進效果
- **空間摺疊**：空間結構彎曲，創造非歐幾里得幾何視覺
- **維度裂縫**：現實與異次元的交匯點
- **時空漣漪**：時間與空間的波動效應

**🌀 物質轉換系統**
- **液態金屬變形**：物體如水銀般流動變形
- **粒子解構重組**：物體分解為粒子後重新組合
- **能量形態轉換**：固體轉化為純能量光束
- **分子重構**：物質在分子層面的實時變化

**🌊 元素操控效果**
- **水流重力**：水違背重力規律向上流動
- **火焰幾何**：火焰形成規整的幾何圖案
- **空氣可視化**：氣流以光線或粒子形式可見
- **光線固化**：光束如實體般可以觸摸和操控

#### 🎭 情感與敘事增強
- **情感張力放大**：強化視覺敘事的情感衝擊力
- **象徵性轉換**：抽象概念的具象化表現
- **夢境邏輯**：非線性的視覺敘事結構
- **潛意識投射**：內心世界的外在化表現

#### 🌟 Creative Mode 反物理效果範例

**重力操控場景**
> "局部重力潮汐在咖啡館中央形成漩渦，椅子和桌子緩緩旋轉上升，咖啡液滴懸浮在半空中形成螺旋星雲，顧客們的頭髮如海藻般向上飄動，重力波紋從地面擴散，創造出夢幻般的用餐體驗。"

**時空變形效果**
> "時間膨脹區域包圍著主角，她的動作變得極其緩慢，而背景中的世界以正常速度運行，空間在她周圍摺疊成非歐幾里得幾何，創造出一個私密的時空膠囊，光線在維度裂縫中彎曲折射。"

**物質轉換場景**
> "主角的身體開始粒子解構，手臂首先分解為發光的金色粒子流，這些粒子在空中重新組合成液態金屬的形態，最終轉化為純能量光束，在攝影機的量子隧道式跟拍下，能量體穿越摺疊的現實層面。"

**元素違規效果**
> "水流逆重力向上奔流，在空中形成晶體般的幾何結構，火焰燃燒成完美的立方體和球體，空氣中的粒子變得可見，形成彩虹色的光線束，這些光束可以被觸摸和塑造成各種形狀。"

#### 🎯 適用場景與應用
**🎨 藝術與實驗創作**
- **前衛藝術影片**：探索非現實視覺語言的藝術作品
- **實驗性短片**：突破傳統敘事的創新影像
- **裝置藝術視覺**：結合反物理概念的互動體驗
- **概念藝術設計**：未來主義和超現實主義創作

**🎬 商業與娛樂應用**
- **科幻電影特效**：反物理效果的視覺設計
- **創意廣告製作**：需要強烈視覺衝擊的品牌廣告
- **音樂影片 (MV)**：富有藝術感和視覺張力的影像
- **遊戲動畫設計**：奇幻世界的視覺效果參考

**🔬 技術與教育領域**
- **科學可視化**：物理概念的藝術化表現
- **教育內容創作**：抽象概念的具象化演示
- **技術展示影片**：未來科技的概念視覺
- **研發概念驗證**：創新想法的視覺化原型

**🌟 創新應用場景**
- **VR/AR 內容設計**：沈浸式體驗的視覺概念
- **品牌概念設計**：突破性的視覺識別系統
- **建築可視化**：反重力建築的概念設計
- **時尚前衛攝影**：超現實的時尚視覺創作

### 🎨 拖放上傳功能
我們提供了現代化的圖片上傳體驗：

#### 上傳方式
- **拖放操作**：將圖片直接拖拽到上傳區域
- **點擊選擇**：點擊上傳區域開啟文件瀏覽器
- **格式支援**：PNG、JPG、JPEG、GIF

#### 智能驗證
- **文件類型檢查**：自動過濾非圖片文件
- **大小限制**：16MB 以內的圖片文件
- **即時提示**：友善的錯誤訊息提醒

#### 預覽功能
- **即時預覽**：上傳後立即顯示圖片
- **文件信息**：顯示文件名稱和大小
- **輕鬆管理**：一鍵移除已選圖片

### 無圖片模式
即使不上傳圖片，系統也能根據您的設定生成豐富的 Prompt：
- 系統會根據場景、主角、時間等參數智能推斷
- Gemini AI 會自動補充合理的視覺描述
- 特別適合快速生成創意 Prompt

## 專案結構
```
vPrompt/
├── app.py                 # Flask 主應用程式
│                         # - Creative Mode 邏輯實現
│                         # - AI 提示詞工程
│                         # - 圖片處理和 API 整合
├── templates/
│   └── index.html         # 主頁面模板
│                         # - Creative Mode UI 組件
│                         # - 響應式設計
│                         # - 多語言支援
├── static/
│   ├── style.css          # 樣式檔案
│   │                     # - Creative Mode 專屬樣式
│   │                     # - 響應式設計 CSS
│   └── script.js          # 前端 JavaScript
│                         # - Creative Mode 狀態管理
│                         # - 拖放上傳功能
├── uploads/               # 圖片上傳目錄
├── requirements.txt       # Python 套件清單
├── .env.example          # 環境變數範例
├── .gitignore            # Git 忽略檔案
└── README.md             # 說明文件
```

## 技術特點
- **後端框架**：Flask + Python 3.12+ 
- **AI 引擎**：Google Gemini 2.0 Flash API 智能處理
- **創意增強**：Creative Mode 深度 AI 提示工程
- **反物理模擬**：突破物理定律的視覺概念生成系統
- **變形引擎**：液態金屬、粒子重組、能量轉換等變形效果
- **時空操控**：時間膨脹、空間摺疊、維度裂縫等概念實現
- **前端技術**：HTML5 + CSS3 + 現代 JavaScript (ES6+)
- **文件上傳**：原生 HTML5 Drag & Drop API
- **用戶介面**：響應式設計，支援桌面和行動裝置
- **多語言支援**：國際化輸出，支援 8 種主要語言
- **狀態管理**：Cookie 技術實現用戶偏好記憶
- **文件處理**：支援多種圖片格式，包含 HEIC（iPhone 格式），16MB 大小限制
- **交互體驗**：流暢動畫效果和即時視覺反饋
- **創意模式**：前衛的提示詞生成技術，突破傳統創作邊界

## 疑難排解

### 常見問題
1. **API Key 錯誤**
   - 確認 `.env` 檔案中的 `GEMINI_API_KEY` 設定正確
   - 檢查 API Key 是否有效且有足夠額度

2. **Creative Mode 沒有效果**
   - 確認已勾選 🎨 Creative Mode 選項
   - Creative Mode 主要增強視覺描述的藝術性和創意性
   - 效果在影片模式下特別明顯

3. **圖片上傳問題**
   - **格式限制**：支援 PNG、JPG、JPEG、GIF、HEIC（iPhone）格式
   - **大小限制**：圖片文件不能超過 16MB
   - **拖放無效**：確保瀏覽器支援 HTML5 拖放功能
   - **權限問題**：檢查 `uploads/` 目錄的寫入權限

4. **拖放功能故障**
   - 確認使用現代瀏覽器（Chrome 60+、Firefox 60+、Safari 12+）
   - 清除瀏覽器緩存並重新載入頁面
   - 檢查 JavaScript 是否正常執行

5. **虛擬環境問題**
   - 確認已啟動虛擬環境
   - 重新安裝相依套件：`pip install -r requirements.txt`

6. **生成結果品質問題**
   - 嘗試啟用 Creative Mode 獲得更豐富的輸出
   - 提供更詳細的場景和角色描述
   - 確保選擇適合的時間和場景設定

## 版本歷史

### v2.1.0 (2025年8月9日) - Creative Mode 版本
- 🎨 新增 Creative Mode 創意模式
- 🎬 突破性攝影機運動建議
- 🌟 增強視覺故事敘述和情感張力
- 🔧 優化 AI 提示詞工程
- 📱 改進響應式設計

### v2.0.0 (2025年7月)
- 📱 完整 HEIC 格式支援
- 🌐 全面響應式設計重構
- 🎯 改善用戶介面體驗
- 🔄 優化拖放上傳功能

### v1.5.0 (2025年6月)
- 🌍 8 種語言支援
- 📄 JSON 格式輸出
- 💾 用戶偏好記憶功能
- 📋 一鍵複製功能

### v1.0.0 (2025年5月)
- 🚀 首次發布
- 🖼️ 基本圖片識別功能
- 🎬 影片提示詞生成
- 📥 文件下載功能

## 未來發展計劃

### v2.2.0 (計劃中)
- 🎥 影片直接上傳分析
- 🔊 音訊提示詞生成
- 🤖 更多 AI 模型支援
- 📊 使用統計分析

### v3.0.0 (長期目標)
- 🌐 多用戶協作功能
- 💾 雲端儲存整合
- 🔒 帳戶系統
- 📈 專業版功能

## 授權
MIT License

## 貢獻
歡迎提交 Issue 和 Pull Request！

### 開發指南
1. **Fork 專案**並建立新分支
2. **遵循程式碼風格**：使用 Python PEP 8 和現代 JavaScript ES6+
3. **測試新功能**：確保 Creative Mode 和其他功能正常運作
4. **更新文檔**：修改功能時同步更新 README

### 貢獻領域
- 🎨 Creative Mode 功能增強
- 🌍 多語言翻譯優化
- 🎬 新的攝影機運動模式
- 📱 行動裝置體驗改善
- 🔧 性能優化和錯誤修復

### 回報問題
請在 [GitHub Issues](https://github.com/elbartohub/vprompt/issues) 中回報：
- 🐛 功能異常或錯誤
- 💡 功能建議和改進想法
- 📝 文檔錯誤或不清楚的地方
