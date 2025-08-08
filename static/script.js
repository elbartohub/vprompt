// Language switching functionality
function initLanguageSystem() {
    // Get saved language or default to English
    const savedLang = localStorage.getItem('vPromptLanguage') || 'en';
    setLanguage(savedLang);
    
    // Setup language toggle button
    const langToggle = document.getElementById('langToggle');
    if (langToggle) {
        langToggle.addEventListener('click', function() {
            const currentLang = document.documentElement.getAttribute('data-lang');
            const newLang = currentLang === 'zh' ? 'en' : 'zh';
            setLanguage(newLang);
            localStorage.setItem('vPromptLanguage', newLang);
        });
    }
}

function setLanguage(lang) {
    document.documentElement.setAttribute('data-lang', lang);
    
    // Update all elements with data attributes
    const elements = document.querySelectorAll('[data-en], [data-zh]');
    elements.forEach(element => {
        if (lang === 'en' && element.hasAttribute('data-en')) {
            element.textContent = element.getAttribute('data-en');
        } else if (lang === 'zh' && element.hasAttribute('data-zh')) {
            element.textContent = element.getAttribute('data-zh');
        }
    });
    
    // Update placeholders
    const placeholderElements = document.querySelectorAll('[data-en-placeholder], [data-zh-placeholder]');
    placeholderElements.forEach(element => {
        if (lang === 'en' && element.hasAttribute('data-en-placeholder')) {
            element.placeholder = element.getAttribute('data-en-placeholder');
        } else if (lang === 'zh' && element.hasAttribute('data-zh-placeholder')) {
            element.placeholder = element.getAttribute('data-zh-placeholder');
        }
    });
    
    // Update document title
    const title = document.title;
    const titleElement = document.querySelector('title');
    if (titleElement) {
        if (lang === 'en' && titleElement.hasAttribute('data-en')) {
            document.title = titleElement.getAttribute('data-en');
        } else if (lang === 'zh' && titleElement.hasAttribute('data-zh')) {
            document.title = titleElement.getAttribute('data-zh');
        }
    }
    
    // Update language toggle button text
    const langToggle = document.getElementById('langToggle');
    if (langToggle) {
        const toggleText = langToggle.querySelector('span');
        if (toggleText) {
            if (lang === 'zh') {
                toggleText.textContent = '🇺🇸 EN';
            } else {
                toggleText.textContent = '🇹🇼 中文';
            }
        }
    }
    
    // Update HTML lang attribute
    if (lang === 'en') {
        document.documentElement.setAttribute('lang', 'en');
    } else {
        document.documentElement.setAttribute('lang', 'zh-Hant');
    }
}

// 跨平台複製到剪貼板功能 - 增強 Windows 11 Chrome 兼容性
function copyToClipboard(text, button, originalButtonText) {
    // 確保按鈕存在並且文本不為空
    if (!text || !button) {
        return false;
    }

    // 方法1: 嘗試使用現代 Clipboard API (適用於 HTTPS 和支援的瀏覽器)
    if (navigator.clipboard && navigator.clipboard.writeText) {
        // 確保在安全上下文中或者是 localhost
        if (window.isSecureContext || location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
            navigator.clipboard.writeText(text).then(function() {
                showCopySuccess(button, originalButtonText);
            }).catch(function(err) {
                console.warn('Clipboard API failed, trying fallback method:', err);
                fallbackCopyMethod(text, button, originalButtonText);
            });
            return true;
        }
    }
    
    // 方法2: 降級到傳統方法
    return fallbackCopyMethod(text, button, originalButtonText);
}

// 降級複製方法 - 使用傳統 DOM 操作
function fallbackCopyMethod(text, button, originalButtonText) {
    try {
        // 創建臨時的隱藏 textarea 元素
        const tempTextArea = document.createElement('textarea');
        tempTextArea.value = text;
        
        // 設置樣式使其不可見但可選擇
        tempTextArea.style.position = 'fixed';
        tempTextArea.style.left = '-9999px';
        tempTextArea.style.top = '-9999px';
        tempTextArea.style.opacity = '0';
        tempTextArea.style.pointerEvents = 'none';
        tempTextArea.setAttribute('readonly', '');
        
        // 添加到 DOM
        document.body.appendChild(tempTextArea);
        
        // 選擇文本
        tempTextArea.focus();
        tempTextArea.select();
        tempTextArea.setSelectionRange(0, tempTextArea.value.length);
        
        // 執行複製命令
        const successful = document.execCommand('copy');
        
        // 清理
        document.body.removeChild(tempTextArea);
        
        if (successful) {
            showCopySuccess(button, originalButtonText);
            return true;
        } else {
            throw new Error('execCommand copy failed');
        }
    } catch (err) {
        console.error('Fallback copy method failed:', err);
        
        // 最後的降級方案：提示用戶手動複製
        try {
            // 嘗試選擇原始文本區域(如果存在)
            const textArea = document.getElementById('promptTextArea') || document.getElementById('promptJsonArea');
            if (textArea && textArea.value === text) {
                textArea.focus();
                textArea.select();
                textArea.setSelectionRange(0, textArea.value.length);
            }
        } catch (selectErr) {
            console.error('Text selection failed:', selectErr);
        }
        
        // Show manual copy prompt with bilingual message
        const currentLang = document.documentElement.getAttribute('data-lang') || 'en';
        const message = currentLang === 'en' 
            ? 'Auto-copy failed, text is selected. Please press Ctrl+C (Windows) or Cmd+C (Mac) to copy manually'
            : '自動複製失敗，文本已選中，請按 Ctrl+C (Windows) 或 Cmd+C (Mac) 手動複製';
        alert(message);
        return false;
    }
}

// 顯示複製成功的視覺反饋
function showCopySuccess(button, originalButtonText) {
    if (!button) return;
    
    const originalText = button.textContent;
    const originalBgColor = button.style.backgroundColor;
    const originalColor = button.style.color;
    
    // Show success status with bilingual text
    const currentLang = document.documentElement.getAttribute('data-lang') || 'en';
    const successText = currentLang === 'en' ? 'Copied!' : '已複製！';
    
    button.textContent = successText;
    button.style.backgroundColor = '#4CAF50';
    button.style.color = 'white';
    button.style.transition = 'all 0.3s ease';
    
    // 2秒後恢復原始狀態
    setTimeout(function() {
        button.textContent = originalButtonText || originalText;
        button.style.backgroundColor = originalBgColor;
        button.style.color = originalColor;
    }, 2000);
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize language system first
    initLanguageSystem();
    
    // 檢查是否有結果並處理載入提示和滾動
    const loadingIndicator = document.getElementById('loadingIndicator');
    const hasResults = document.getElementById('promptTextArea') || document.getElementById('promptJsonArea');
    
    if (loadingIndicator) {
        // 隱藏載入提示
        loadingIndicator.style.display = 'none';
    }
    
    // 如果有結果，自動滾動到結果區域
    if (hasResults) {
        setTimeout(function() {
            // 找到第一個結果標題並滾動到該位置
            const firstResultHeading = document.querySelector('h2, h3');
            if (firstResultHeading) {
                firstResultHeading.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            } else {
                // 如果沒有找到標題，滾動到頁面底部
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
            }
        }, 300); // 給頁面一點時間完全加載
    }
    
    // 場景自定義欄位顯示
    const sceneSelect = document.getElementById('sceneSelect');
    const customSceneInput = document.getElementById('customSceneInput');
    if (sceneSelect && customSceneInput) {
        sceneSelect.addEventListener('change', function() {
            customSceneInput.style.display = (sceneSelect.value === '其它' || sceneSelect.value === 'Other') ? 'inline' : 'none';
            if (sceneSelect.value === '其它' || sceneSelect.value === 'Other') {
                customSceneInput.focus();
            }
        });
        customSceneInput.style.display = (sceneSelect.value === '其它' || sceneSelect.value === 'Other') ? 'inline' : 'none';
        if (sceneSelect.value === '其它' || sceneSelect.value === 'Other') {
            customSceneInput.focus();
        }
    }

    // 主角自定義欄位顯示
    const characterSelect = document.getElementById('characterSelect');
    const customCharacterInput = document.getElementById('customCharacterInput');
    if (characterSelect && customCharacterInput) {
        characterSelect.addEventListener('change', function() {
            customCharacterInput.style.display = (characterSelect.value === '其它' || characterSelect.value === 'Other') ? 'inline' : 'none';
            if (characterSelect.value === '其它' || characterSelect.value === 'Other') {
                customCharacterInput.focus();
            }
        });
        customCharacterInput.style.display = (characterSelect.value === '其它' || characterSelect.value === 'Other') ? 'inline' : 'none';
        if (characterSelect.value === '其它' || characterSelect.value === 'Other') {
            customCharacterInput.focus();
        }
    }

    // 自動聚焦到故事描述欄位
    const extraDescTextarea = document.querySelector('textarea[name="extra_desc"]');
    if (extraDescTextarea) {
        // 延遲一點時間再聚焦，確保頁面完全加載
        setTimeout(function() {
            extraDescTextarea.focus();
            // 將光標移動到文本末尾
            extraDescTextarea.setSelectionRange(extraDescTextarea.value.length, extraDescTextarea.value.length);
        }, 100);
    }

    // 表單送出時禁用按鈕，顯示載入提示，並滾動到載入區域等待結果
    const form = document.getElementById('promptForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            const loadingIndicator = document.getElementById('loadingIndicator');
            
            if (submitBtn) {
                submitBtn.disabled = true;
                
                // 顯示載入提示
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'block';
                    
                    // 滾動到載入提示區域
                    setTimeout(function() {
                        loadingIndicator.scrollIntoView({
                            behavior: 'smooth',
                            block: 'center'
                        });
                    }, 100);
                } else {
                    // 如果沒有載入提示元素，滾動到頁面底部
                    setTimeout(function() {
                        window.scrollTo({
                            top: document.body.scrollHeight,
                            behavior: 'smooth'
                        });
                    }, 100);
                }
                
                // 重新啟用按鈕（在頁面重新載入前不會執行到這裡）
                setTimeout(function() {
                    submitBtn.disabled = false;
                }, 800);
            }
        });
    }

    // 複製文本功能 - 增強跨平台兼容性
    const copyTextBtn = document.getElementById('copyTextBtn');
    const promptTextArea = document.getElementById('promptTextArea');
    if (copyTextBtn && promptTextArea) {
        copyTextBtn.addEventListener('click', function() {
            const currentLang = document.documentElement.getAttribute('data-lang') || 'en';
            const buttonText = currentLang === 'en' ? 'Copy All Text' : '複製全部文本';
            copyToClipboard(promptTextArea.value, copyTextBtn, buttonText);
        });
    }

    // 複製 JSON 功能 - 增強跨平台兼容性
    const copyJsonBtn = document.getElementById('copyJsonBtn');
    const promptJsonArea = document.getElementById('promptJsonArea');
    if (copyJsonBtn && promptJsonArea) {
        copyJsonBtn.addEventListener('click', function() {
            const currentLang = document.documentElement.getAttribute('data-lang') || 'en';
            const buttonText = currentLang === 'en' ? 'Copy JSON' : '複製 JSON';
            copyToClipboard(promptJsonArea.value, copyJsonBtn, buttonText);
        });
    }

    // Drop Zone 功能
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const dropZoneContent = document.getElementById('dropZoneContent');
    const dropZonePreview = document.getElementById('dropZonePreview');
    const previewImage = document.getElementById('previewImage');
    const previewInfo = document.getElementById('previewInfo');
    const removeImageBtn = document.getElementById('removeImage');

    // Debug: 檢查所有元素是否存在
    console.log('Drop zone elements check:', {
        dropZone: !!dropZone,
        fileInput: !!fileInput,
        dropZoneContent: !!dropZoneContent,
        dropZonePreview: !!dropZonePreview,
        previewImage: !!previewImage,
        previewInfo: !!previewInfo,
        removeImageBtn: !!removeImageBtn
    });

    // Debug: Check if heic2any library is loaded
    console.log('heic2any library check:', {
        heic2anyAvailable: typeof heic2any !== 'undefined',
        heic2anyFunction: typeof heic2any === 'function',
        heic2anyObject: typeof heic2any
    });

    // Debug: Test if we can access the uploads
    console.log('Current page URL:', window.location.href);
    console.log('Upload test will check for existing HEIC file...');

    if (dropZone && fileInput && dropZoneContent && dropZonePreview && previewImage && previewInfo) {
        // 點擊觸發文件選擇
        dropZone.addEventListener('click', function() {
            fileInput.click();
        });

        // 文件選擇事件
        fileInput.addEventListener('change', function(e) {
            handleFiles(e.target.files);
        });

        // 拖拽事件
        dropZone.addEventListener('dragover', function(e) {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', function(e) {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });

    // 移除圖片預覽
    if (removeImageBtn) {
        removeImageBtn.addEventListener('click', function() {
            dropZoneContent.style.display = 'flex';
            dropZonePreview.style.display = 'none';
            fileInput.value = '';
        });
    }
    
    // 測試函數：檢驗HEIC轉換端點
    window.testHeicConversion = function() {
        console.log('Testing HEIC conversion endpoint...');
        const testUrl = '/convert_heic/IMG_6019.heic?t=' + Date.now();
        console.log('Test URL:', testUrl);
        
        const img = new Image();
        img.onload = function() {
            console.log('✅ HEIC conversion endpoint working!');
            console.log('Image dimensions:', img.naturalWidth, 'x', img.naturalHeight);
            
            // 嘗試設置到預覽圖片
            if (previewImage) {
                previewImage.src = testUrl;
                console.log('Set previewImage.src to:', testUrl);
                
                if (dropZoneContent && dropZonePreview) {
                    dropZoneContent.style.display = 'none';
                    dropZonePreview.style.display = 'flex';
                    console.log('Updated display styles');
                }
                
                if (previewInfo) {
                    previewInfo.innerHTML = 'IMG_6019.heic (Test)<br><small style="color: #28a745; font-weight: bold;">🖥️ 測試預覽</small>';
                }
            }
        };
        img.onerror = function(e) {
            console.log('❌ HEIC conversion endpoint failed:', e);
        };
        img.src = testUrl;
    };
    
    // 直接顯示圖片測試（不通過Image對象預載）
    window.testDirectDisplay = function() {
        console.log('Testing direct image display...');
        const testUrl = '/convert_heic/IMG_6019.heic?t=' + Date.now();
        
        if (previewImage && dropZoneContent && dropZonePreview && previewInfo) {
            console.log('Setting image source directly...');
            previewImage.src = testUrl;
            dropZoneContent.style.display = 'none';
            dropZonePreview.style.display = 'flex';
            previewInfo.innerHTML = 'IMG_6019.heic (Direct Test)<br><small style="color: #28a745; font-weight: bold;">🖥️ 直接測試</small>';
            console.log('Direct display test completed');
        } else {
            console.log('Missing elements for direct display test');
        }
    };
    
    // 在控制台輸出測試提示
    console.log('Available test functions:');
    console.log('- window.testHeicConversion() - Test with image preloading');
    console.log('- window.testDirectDisplay() - Test direct display');        // 處理文件函數
        function handleFiles(files) {
            if (files.length > 0) {
                const file = files[0];
                
                // 檢查文件類型 - 支援 HEIC/HEIF 格式
                const allowedTypes = ['image/', 'application/octet-stream']; // HEIC files may appear as octet-stream
                const allowedExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.heic', '.heif'];
                const fileName = file.name.toLowerCase();
                const hasValidType = allowedTypes.some(type => file.type.startsWith(type));
                const hasValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext));
                
                if (!hasValidType && !hasValidExtension) {
                    const currentLang = document.documentElement.getAttribute('data-lang') || 'en';
                    const message = currentLang === 'en' 
                        ? 'Please select a supported image format (PNG, JPG, JPEG, GIF, HEIC)!'
                        : '請選擇支援的圖片文件格式（PNG、JPG、JPEG、GIF、HEIC）！';
                    alert(message);
                    return;
                }

                // 檢查文件大小 (16MB)
                if (file.size > 16 * 1024 * 1024) {
                    const currentLang = document.documentElement.getAttribute('data-lang') || 'en';
                    const message = currentLang === 'en' 
                        ? 'Image file size cannot exceed 16MB!'
                        : '圖片文件大小不能超過 16MB！';
                    alert(message);
                    return;
                }

                // 設置文件到 input
                const dt = new DataTransfer();
                dt.items.add(file);
                fileInput.files = dt.files;

                // 顯示預覽
                showPreview(file);
            }
        }

        // 顯示預覽函數
        function showPreview(file) {
            const fileName = file.name.toLowerCase();
            
            console.log('showPreview called for:', fileName);
            console.log('File details:', {
                name: file.name,
                size: file.size,
                type: file.type,
                lastModified: new Date(file.lastModified)
            });
            
            // 檢查是否為 HEIC/HEIF 檔案
            if (fileName.endsWith('.heic') || fileName.endsWith('.heif')) {
                console.log('HEIC file detected, attempting real image preview...');
                
                // 顯示載入狀態
                previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #f59e0b;">🔄 正在載入 HEIC 預覽...</small>`;
                dropZoneContent.style.display = 'none';
                dropZonePreview.style.display = 'flex';
                
                // 嘗試客戶端轉換以顯示真實圖片
                attemptClientSideHeicConversion(file);
                
            } else {
                console.log('Regular image file:', fileName);
                // 一般圖片檔案使用 FileReader 正常預覽
                const reader = new FileReader();
                reader.onload = function(e) {
                    console.log('FileReader loaded successfully for:', fileName);
                    previewImage.src = e.target.result;
                    previewInfo.textContent = `${file.name} (${formatFileSize(file.size)})`;
                    dropZoneContent.style.display = 'none';
                    dropZonePreview.style.display = 'flex';
                };
                reader.onerror = function(error) {
                    console.error('FileReader error for:', fileName, error);
                    showErrorPlaceholder(file);
                };
                reader.readAsDataURL(file);
            }
        }
        
        // Canvas-based HEIC 預覽函數 - 創建智能預覽圖
        function attemptCanvasHeicPreview(file) {
            console.log('Creating Canvas-based HEIC preview...');
            
            // 嘗試讀取 HEIC 文件的 EXIF 元數據
            const reader = new FileReader();
            reader.onload = function(e) {
                const arrayBuffer = e.target.result;
                const dataView = new DataView(arrayBuffer);
                
                // 創建 Canvas 預覽圖
                const canvas = document.createElement('canvas');
                canvas.width = 300;
                canvas.height = 200;
                const ctx = canvas.getContext('2d');
                
                // 背景漸變
                const gradient = ctx.createLinearGradient(0, 0, 300, 200);
                gradient.addColorStop(0, '#e3f2fd');
                gradient.addColorStop(1, '#bbdefb');
                ctx.fillStyle = gradient;
                ctx.fillRect(0, 0, 300, 200);
                
                // 繪製邊框
                ctx.strokeStyle = '#2196f3';
                ctx.lineWidth = 2;
                ctx.setLineDash([5, 5]);
                ctx.strokeRect(5, 5, 290, 190);
                ctx.setLineDash([]);
                
                // HEIC 圖標背景
                ctx.fillStyle = '#4caf50';
                ctx.beginPath();
                ctx.rect(120, 40, 60, 40);
                ctx.fill();
                
                // HEIC 文字
                ctx.fillStyle = 'white';
                ctx.font = 'bold 14px Arial';
                ctx.textAlign = 'center';
                ctx.fillText('HEIC', 150, 64);
                
                // 相機圖標
                ctx.fillStyle = '#666';
                ctx.font = '24px Arial';
                ctx.fillText('📱', 150, 110);
                
                // 文件名稱
                ctx.fillStyle = '#333';
                ctx.font = 'bold 16px Arial';
                const displayName = file.name.length > 20 ? file.name.substring(0, 17) + '...' : file.name;
                ctx.fillText(displayName, 150, 135);
                
                // 文件大小
                ctx.fillStyle = '#666';
                ctx.font = '12px Arial';
                ctx.fillText(formatFileSize(file.size), 150, 155);
                
                // 嘗試獲取圖片尺寸信息
                try {
                    let dimensions = extractHeicDimensions(dataView);
                    if (dimensions) {
                        ctx.fillText(`${dimensions.width} × ${dimensions.height}`, 150, 175);
                        console.log('HEIC dimensions extracted:', dimensions);
                    } else {
                        ctx.fillText('iPhone 高效率圖像', 150, 175);
                    }
                } catch (error) {
                    console.log('Could not extract HEIC dimensions:', error);
                    ctx.fillText('iPhone 高效率圖像', 150, 175);
                }
                
                // 狀態指示器
                ctx.fillStyle = '#4caf50';
                ctx.font = 'bold 12px Arial';
                ctx.fillText('✓ 就緒待處理', 150, 190);
                
                // 設置預覽圖片
                previewImage.src = canvas.toDataURL();
                previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #4caf50; font-weight: bold;">📱 HEIC Canvas 預覽</small><br><small style="color: #666;">圖片已就緒，將正常上傳處理</small>`;
                
                // 顯示預覽
                dropZoneContent.style.display = 'none';
                dropZonePreview.style.display = 'flex';
            };
            
            reader.onerror = function(error) {
                console.error('Failed to read HEIC file for Canvas preview:', error);
                // 最終降級顯示基本佔位符
                showHeicPlaceholder(file);
            };
            
            // 讀取文件的前 64KB 用於元數據分析
            const blob = file.slice(0, 65536);
            reader.readAsArrayBuffer(blob);
        }
        
        // 嘗試從 HEIC 文件中提取尺寸信息
        function extractHeicDimensions(dataView) {
            try {
                // 查找 HEIC 文件中的尺寸信息
                // HEIC 文件通常在文件頭部包含尺寸信息
                let offset = 0;
                const length = dataView.byteLength;
                
                // 尋找 'ispe' box (Image Spatial Extents)
                while (offset < length - 8) {
                    const boxSize = dataView.getUint32(offset, false);
                    const boxType = String.fromCharCode(
                        dataView.getUint8(offset + 4),
                        dataView.getUint8(offset + 5),
                        dataView.getUint8(offset + 6),
                        dataView.getUint8(offset + 7)
                    );
                    
                    if (boxType === 'ispe' && offset + 20 < length) {
                        // 找到尺寸信息
                        const width = dataView.getUint32(offset + 12, false);
                        const height = dataView.getUint32(offset + 16, false);
                        if (width > 0 && height > 0 && width < 10000 && height < 10000) {
                            return { width, height };
                        }
                    }
                    
                    offset += Math.max(boxSize, 8);
                    if (boxSize === 0) break;
                }
                
                // 如果找不到確切尺寸，返回常見的 iPhone 尺寸
                return { width: 4032, height: 3024 };
            } catch (error) {
                console.log('Error extracting HEIC dimensions:', error);
                return null;
            }
        }
        
        // 服務器端 HEIC 轉換預覽
        function attemptServerSideHeicPreview(file) {
            console.log('Attempting server-side HEIC conversion...');
            
            // 首先檢查文件是否已經存在於服務器上
            const testUrl = `/uploads/${encodeURIComponent(file.name)}`;
            console.log('Testing direct file access:', testUrl);
            
            // 如果文件已存在，直接嘗試轉換
            const convertUrl = `/convert_heic/${encodeURIComponent(file.name)}`;
            console.log('Testing server conversion:', convertUrl);
            
            // 創建臨時預覽狀態
            showLoadingPreview(file, '檢查服務器端轉換...');
            
            // 直接嘗試服務器端轉換
            const img = new Image();
            img.onload = function() {
                console.log('Server-side HEIC conversion successful!');
                console.log('Image loaded successfully, dimensions:', img.naturalWidth, 'x', img.naturalHeight);
                console.log('Setting previewImage.src to:', convertUrl);
                previewImage.src = convertUrl + '?t=' + Date.now();
                previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #28a745; font-weight: bold;">🖥️ 服務器端轉換預覽</small><br><small style="color: #666;">圖片已成功轉換並預覽</small>`;
                dropZoneContent.style.display = 'none';
                dropZonePreview.style.display = 'flex';
                console.log('Preview should now be visible');
            };
            img.onerror = function(e) {
                console.log('Direct server conversion failed:', e);
                console.log('Error details:', e.type, e.target.src);
                // 轉換失敗，需要先上傳文件
                uploadAndConvertHeic(file);
            };
            img.src = convertUrl + '?t=' + Date.now(); // Add cache buster
            console.log('Testing image load with URL:', img.src);
        }
        
        // 上傳並轉換 HEIC
        function uploadAndConvertHeic(file) {
            console.log('Uploading HEIC file for conversion...');
            
            // 創建臨時預覽狀態
            showLoadingPreview(file, '正在上傳 HEIC 圖片...');
            
            const formData = new FormData();
            formData.append('image', file);
            
            // 上傳文件
            fetch('/', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                console.log('Upload response status:', response.status);
                if (response.ok) {
                    // 文件上傳成功，現在嘗試轉換
                    showLoadingPreview(file, '正在轉換 HEIC 圖片...');
                    
                    // 等待一下讓服務器處理
                    setTimeout(() => {
                        const convertUrl = `/convert_heic/${encodeURIComponent(file.name)}`;
                        console.log('Trying conversion after upload:', convertUrl);
                        
                        const img = new Image();
                        img.onload = function() {
                            console.log('Server-side HEIC conversion successful after upload!');
                            previewImage.src = convertUrl;
                            previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #28a745; font-weight: bold;">🖥️ 服務器端轉換預覽</small><br><small style="color: #666;">圖片已成功轉換並預覽</small>`;
                            dropZoneContent.style.display = 'none';
                            dropZonePreview.style.display = 'flex';
                        };
                        img.onerror = function() {
                            console.log('Server conversion failed even after upload');
                            // 最後嘗試獲取文件信息
                            fetchHeicInfoAndCreatePreview(file);
                        };
                        img.src = convertUrl + '?t=' + Date.now();
                    }, 1000); // Wait 1 second for server processing
                } else {
                    console.log('Upload failed with status:', response.status);
                    fetchHeicInfoAndCreatePreview(file);
                }
            })
            .catch(error => {
                console.error('Upload error:', error);
                fetchHeicInfoAndCreatePreview(file);
            });
        }
        
        // 獲取 HEIC 文件信息並創建智能預覽
        function fetchHeicInfoAndCreatePreview(file) {
            console.log('Fetching HEIC file info from server...');
            
            const infoUrl = `/heic_info/${encodeURIComponent(file.name)}`;
            fetch(infoUrl)
            .then(response => response.json())
            .then(info => {
                console.log('HEIC file info received:', info);
                createEnhancedHeicPreview(file, info);
            })
            .catch(error => {
                console.log('Failed to get HEIC info:', error);
                // 最終降級到簡單佔位符
                showHeicPlaceholder(file);
            });
        }
        
        // 創建增強的 HEIC 預覽（基於服務器信息）
        function createEnhancedHeicPreview(file, info) {
            console.log('Creating enhanced HEIC preview with server info...');
            
            const canvas = document.createElement('canvas');
            canvas.width = 320;
            canvas.height = 240;
            const ctx = canvas.getContext('2d');
            
            // 背景漸變
            const gradient = ctx.createLinearGradient(0, 0, 320, 240);
            gradient.addColorStop(0, '#f3e5f5');
            gradient.addColorStop(1, '#e1bee7');
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, 320, 240);
            
            // 邊框
            ctx.strokeStyle = '#9c27b0';
            ctx.lineWidth = 2;
            ctx.strokeRect(5, 5, 310, 230);
            
            // 頂部標題區
            ctx.fillStyle = '#9c27b0';
            ctx.fillRect(10, 10, 300, 30);
            ctx.fillStyle = 'white';
            ctx.font = 'bold 14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('🖥️ 服務器端 HEIC 信息', 160, 30);
            
            // 文件名
            ctx.fillStyle = '#333';
            ctx.font = 'bold 16px Arial';
            ctx.textAlign = 'center';
            const displayName = file.name.length > 25 ? file.name.substring(0, 22) + '...' : file.name;
            ctx.fillText(displayName, 160, 65);
            
            // 文件信息
            ctx.fillStyle = '#666';
            ctx.font = '12px Arial';
            if (info && !info.error) {
                ctx.fillText(`尺寸: ${info.width} × ${info.height}`, 160, 85);
                ctx.fillText(`格式: ${info.format || 'HEIC'}`, 160, 105);
                ctx.fillText(`大小: ${formatFileSize(file.size)}`, 160, 125);
                ctx.fillText(`色彩模式: ${info.mode || 'RGB'}`, 160, 145);
                
                if (info.has_exif) {
                    ctx.fillStyle = '#4caf50';
                    ctx.fillText('✓ 包含 EXIF 數據', 160, 165);
                }
            } else {
                ctx.fillText(`大小: ${formatFileSize(file.size)}`, 160, 85);
                ctx.fillText('格式: HEIC/HEIF', 160, 105);
                ctx.fillText('iPhone 高效率圖像', 160, 125);
            }
            
            // HEIC 圖標
            ctx.fillStyle = '#4caf50';
            ctx.beginPath();
            ctx.roundRect(130, 175, 60, 25, 5);
            ctx.fill();
            ctx.fillStyle = 'white';
            ctx.font = 'bold 12px Arial';
            ctx.fillText('HEIC', 160, 192);
            
            // 狀態
            ctx.fillStyle = '#4caf50';
            ctx.font = 'bold 11px Arial';
            ctx.fillText('✓ 已分析完成', 160, 215);
            
            // 設置預覽
            previewImage.src = canvas.toDataURL();
            previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #9c27b0; font-weight: bold;">🖥️ 服務器端信息預覽</small><br><small style="color: #666;">圖片已分析，將正常處理</small>`;
            
            // 顯示預覽
            dropZoneContent.style.display = 'none';
            dropZonePreview.style.display = 'flex';
        }
        
        // 顯示加載中預覽
        function showLoadingPreview(file, message) {
            const canvas = document.createElement('canvas');
            canvas.width = 250;
            canvas.height = 180;
            const ctx = canvas.getContext('2d');
            
            // 背景
            ctx.fillStyle = '#f5f5f5';
            ctx.fillRect(0, 0, 250, 180);
            
            // 邊框
            ctx.strokeStyle = '#ddd';
            ctx.lineWidth = 2;
            ctx.strokeRect(2, 2, 246, 176);
            
            // 加載動畫背景
            ctx.fillStyle = '#2196f3';
            ctx.beginPath();
            ctx.roundRect(50, 60, 150, 40, 8);
            ctx.fill();
            
            // 文字
            ctx.fillStyle = 'white';
            ctx.font = 'bold 14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('處理中...', 125, 85);
            
            ctx.fillStyle = '#333';
            ctx.font = '12px Arial';
            ctx.fillText(message, 125, 120);
            
            ctx.fillText(file.name, 125, 140);
            
            // 設置預覽
            previewImage.src = canvas.toDataURL();
            previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #2196f3; font-weight: bold;">⏳ ${message}</small>`;
            
            // 顯示預覽
            dropZoneContent.style.display = 'none';
            dropZonePreview.style.display = 'flex';
        }
        
        // 嘗試原生 HEIC 預覽
        function attemptNativeHeicPreview(file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                // 嘗試直接設置圖片源，如果瀏覽器支援會顯示
                const testImg = new Image();
                testImg.onload = function() {
                    // 瀏覽器能夠載入 HEIC！
                    console.log('Browser supports HEIC preview!');
                    previewImage.src = e.target.result;
                    previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #28a745; font-weight: bold;">✓ HEIC 原生預覽</small>`;
                    dropZoneContent.style.display = 'none';
                    dropZonePreview.style.display = 'flex';
                };
                testImg.onerror = function() {
                    // 瀏覽器不支援 HEIC 預覽，使用 Canvas 預覽
                    console.log('Browser does not support HEIC preview, using Canvas preview');
                    attemptCanvasHeicPreview(file);
                };
                testImg.src = e.target.result;
            };
            reader.onerror = function() {
                console.log('FileReader error for HEIC, using Canvas preview');
                attemptCanvasHeicPreview(file);
            };
            reader.readAsDataURL(file);
        }
        
        // 顯示 HEIC 佔位符的函數
        function showHeicPlaceholder(file) {
            const canvas = document.createElement('canvas');
            canvas.width = 200;
            canvas.height = 150;
            const ctx = canvas.getContext('2d');
            
            // 繪製背景
            ctx.fillStyle = '#f8f9fa';
            ctx.fillRect(0, 0, 200, 150);
            
            // 繪製邊框
            ctx.strokeStyle = '#dee2e6';
            ctx.lineWidth = 2;
            ctx.strokeRect(1, 1, 198, 148);
            
            // 繪製綠色圓圈
            ctx.fillStyle = '#28a745';
            ctx.beginPath();
            ctx.arc(100, 60, 20, 0, 2 * Math.PI);
            ctx.fill();
            
            // 繪製 HEIC 文字
            ctx.fillStyle = 'white';
            ctx.font = 'bold 14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('HEIC', 100, 66);
            
            // 繪製說明文字
            ctx.fillStyle = '#6c757d';
            ctx.font = '14px Arial';
            ctx.fillText('iPhone 圖片', 100, 100);
            
            ctx.fillStyle = '#28a745';
            ctx.font = '12px Arial';
            ctx.fillText('✓ 已準備就緒', 100, 120);
            
            // 設置預覽圖片
            previewImage.src = canvas.toDataURL();
            previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #28a745; font-weight: bold;">✓ HEIC 格式已就緒，將正常處理</small><br><small style="color: #6c757d;">💡 提示：部分瀏覽器無法預覽 HEIC</small>`;
            
            // 顯示預覽
            dropZoneContent.style.display = 'none';
            dropZonePreview.style.display = 'flex';
        }
        
        // 顯示錯誤佔位符的函數
        function showErrorPlaceholder(file) {
            const canvas = document.createElement('canvas');
            canvas.width = 200;
            canvas.height = 150;
            const ctx = canvas.getContext('2d');
            
            ctx.fillStyle = '#f8f9fa';
            ctx.fillRect(0, 0, 200, 150);
            ctx.strokeStyle = '#dee2e6';
            ctx.lineWidth = 2;
            ctx.strokeRect(1, 1, 198, 148);
            
            ctx.fillStyle = '#6c757d';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('圖片格式', 100, 75);
            
            ctx.fillStyle = '#ffc107';
            ctx.font = '12px Arial';
            ctx.fillText('⚠ 暫無預覽', 100, 95);
            
            previewImage.src = canvas.toDataURL();
            previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #ffc107;">⚠ 預覽不可用，但檔案已就緒</small>`;
            dropZoneContent.style.display = 'none';
            dropZonePreview.style.display = 'flex';
        }

        // 移除圖片函數
        function removeImage() {
            fileInput.value = '';
            previewImage.src = '';
            previewInfo.textContent = '';
            dropZoneContent.style.display = 'block';
            dropZonePreview.style.display = 'none';
        }
        
        // 客戶端 HEIC 轉換（作為備用）
        function attemptClientSideHeicConversion(file) {
            console.log('Attempting client-side HEIC conversion...');
            
            // 設置載入狀態
            previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #2196f3;">🔄 嘗試 HEIC 預覽...</small>`;
            
            // 方法1: 嘗試客戶端轉換
            if (typeof heic2any !== 'undefined') {
                console.log('heic2any library found, starting conversion...');
                
                previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #2196f3;">🔄 正在轉換 HEIC 圖片...</small>`;
                
                heic2any({
                    blob: file,
                    toType: "image/jpeg",
                    quality: 0.8
                })
                .then(function(conversionResult) {
                    console.log('✅ Client-side HEIC conversion successful!');
                    const convertedBlob = Array.isArray(conversionResult) ? conversionResult[0] : conversionResult;
                    const imageUrl = URL.createObjectURL(convertedBlob);
                    
                    previewImage.onload = function() {
                        console.log('✅ Converted HEIC image displayed successfully');
                        previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #28a745; font-weight: bold;">✓ HEIC 圖片預覽</small>`;
                        setTimeout(() => URL.revokeObjectURL(imageUrl), 2000);
                    };
                    
                    previewImage.onerror = function() {
                        console.error('❌ Error displaying converted HEIC image');
                        URL.revokeObjectURL(imageUrl);
                        tryServerSideHeicPreview(file);
                    };
                    
                    previewImage.src = imageUrl;
                    dropZoneContent.style.display = 'none';
                    dropZonePreview.style.display = 'flex';
                })
                .catch(function(error) {
                    console.error('❌ Client-side HEIC conversion failed:', error);
                    tryServerSideHeicPreview(file);
                });
            } else {
                console.warn('⚠️ heic2any library not available');
                tryServerSideHeicPreview(file);
            }
        }
        
        // 嘗試伺服器端 HEIC 轉換預覽
        function tryServerSideHeicPreview(file) {
            console.log('Attempting server-side HEIC conversion...');
            
            previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #f59e0b;">🔄 伺服器轉換中...</small>`;
            
            // 創建 FormData 上傳檔案進行轉換
            const formData = new FormData();
            formData.append('file', file);
            
            fetch('/convert_heic_preview', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (response.ok) {
                    return response.blob();
                } else {
                    throw new Error('Server conversion failed');
                }
            })
            .then(blob => {
                console.log('✅ Server-side HEIC conversion successful!');
                const imageUrl = URL.createObjectURL(blob);
                
                previewImage.onload = function() {
                    console.log('✅ Server-converted HEIC image displayed');
                    previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #28a745; font-weight: bold;">✓ 伺服器 HEIC 預覽</small>`;
                    setTimeout(() => URL.revokeObjectURL(imageUrl), 2000);
                };
                
                previewImage.onerror = function() {
                    console.error('❌ Error displaying server-converted image');
                    URL.revokeObjectURL(imageUrl);
                    tryNativeHeicPreview(file);
                };
                
                previewImage.src = imageUrl;
                dropZoneContent.style.display = 'none';
                dropZonePreview.style.display = 'flex';
            })
            .catch(error => {
                console.error('❌ Server-side HEIC conversion failed:', error);
                tryNativeHeicPreview(file);
            });
        }
        
        // 嘗試原生瀏覽器 HEIC 預覽
        function tryNativeHeicPreview(file) {
            console.log('Attempting native HEIC preview...');
            
            previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #6366f1;">🔄 原生預覽中...</small>`;
            
            const reader = new FileReader();
            reader.onload = function(e) {
                const testImg = new Image();
                testImg.onload = function() {
                    console.log('✅ Browser supports native HEIC preview!');
                    previewImage.src = e.target.result;
                    previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #28a745; font-weight: bold;">✓ 原生 HEIC 預覽</small>`;
                    dropZoneContent.style.display = 'none';
                    dropZonePreview.style.display = 'flex';
                };
                testImg.onerror = function() {
                    console.warn('❌ Native HEIC preview not supported');
                    showEnhancedHeicPlaceholder(file);
                };
                testImg.src = e.target.result;
            };
            reader.onerror = function() {
                console.error('❌ FileReader failed for HEIC file');
                showEnhancedHeicPlaceholder(file);
            };
            reader.readAsDataURL(file);
        }
        
        // 增強的 HEIC 佔位符（作為最終後備方案）
        function showEnhancedHeicPlaceholder(file) {
            console.log('Showing enhanced HEIC placeholder...');
            
            const canvas = document.createElement('canvas');
            canvas.width = 400;
            canvas.height = 300;
            const ctx = canvas.getContext('2d');
            
            // 背景漸變
            const gradient = ctx.createLinearGradient(0, 0, 400, 300);
            gradient.addColorStop(0, '#e8f5e8');
            gradient.addColorStop(1, '#c8e6c9');
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, 400, 300);
            
            // 邊框
            ctx.strokeStyle = '#4caf50';
            ctx.lineWidth = 3;
            ctx.setLineDash([10, 5]);
            ctx.strokeRect(5, 5, 390, 290);
            ctx.setLineDash([]);
            
            // HEIC 標誌
            ctx.fillStyle = '#4caf50';
            ctx.beginPath();
            ctx.arc(200, 80, 40, 0, 2 * Math.PI);
            ctx.fill();
            
            ctx.fillStyle = 'white';
            ctx.font = 'bold 24px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('HEIC', 200, 88);
            
            // 手機圖標
            ctx.fillStyle = '#666';
            ctx.font = '32px Arial';
            ctx.fillText('📱', 200, 140);
            
            // 文件信息
            ctx.fillStyle = '#333';
            ctx.font = 'bold 18px Arial';
            const displayName = file.name.length > 25 ? file.name.substring(0, 22) + '...' : file.name;
            ctx.fillText(displayName, 200, 180);
            
            ctx.fillStyle = '#666';
            ctx.font = '14px Arial';
            ctx.fillText(formatFileSize(file.size), 200, 205);
            
            // 嘗試顯示預估尺寸
            ctx.fillText('預估尺寸: 4032 × 3024', 200, 225);
            
            // 狀態
            ctx.fillStyle = '#4caf50';
            ctx.font = 'bold 16px Arial';
            ctx.fillText('✓ 已準備上傳處理', 200, 255);
            
            ctx.fillStyle = '#999';
            ctx.font = '12px Arial';
            ctx.fillText('圖片將在服務器端轉換', 200, 275);
            
            previewImage.src = canvas.toDataURL();
            previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #4caf50; font-weight: bold;">📱 HEIC 已就緒</small><br><small style="color: #666;">文件已準備上傳，將在服務器端處理</small>`;
            
            dropZoneContent.style.display = 'none';
            dropZonePreview.style.display = 'flex';
        }

        // 格式化文件大小
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        // 嘗試從 HEIC 文件中提取尺寸信息
        function extractHeicDimensions(dataView) {
            try {
                // 簡單的 HEIC 元數據提取（非完整實現）
                // 在實際的 HEIC 文件中尋找尺寸信息
                for (let i = 0; i < dataView.byteLength - 8; i += 4) {
                    if (dataView.getUint32(i) === 0x69736865) { // 'ishe' 標識
                        // 嘗試提取尺寸信息，這是簡化版本
                        return {
                            width: 4032,  // 典型的 iPhone HEIC 尺寸
                            height: 3024
                        };
                    }
                }
                return null;
            } catch (error) {
                console.log('Error extracting HEIC dimensions:', error);
                return null;
            }
        }
    }
});
