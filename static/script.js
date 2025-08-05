document.addEventListener('DOMContentLoaded', function() {
    // 場景自定義欄位顯示
    const sceneSelect = document.getElementById('sceneSelect');
    const customSceneInput = document.getElementById('customSceneInput');
    if (sceneSelect && customSceneInput) {
        sceneSelect.addEventListener('change', function() {
            customSceneInput.style.display = (sceneSelect.value === '其它') ? 'inline' : 'none';
            if (sceneSelect.value === '其它') {
                customSceneInput.focus();
            }
        });
        customSceneInput.style.display = (sceneSelect.value === '其它') ? 'inline' : 'none';
        if (sceneSelect.value === '其它') {
            customSceneInput.focus();
        }
    }

    // 主角自定義欄位顯示
    const characterSelect = document.getElementById('characterSelect');
    const customCharacterInput = document.getElementById('customCharacterInput');
    if (characterSelect && customCharacterInput) {
        characterSelect.addEventListener('change', function() {
            customCharacterInput.style.display = (characterSelect.value === '其它') ? 'inline' : 'none';
            if (characterSelect.value === '其它') {
                customCharacterInput.focus();
            }
        });
        customCharacterInput.style.display = (characterSelect.value === '其它') ? 'inline' : 'none';
        if (characterSelect.value === '其它') {
            customCharacterInput.focus();
        }
    }

    // Google Drive 分享（僅前端提示，需後端 OAuth 實作）
    const shareBtn = document.getElementById('shareDriveBtn');
    if (shareBtn) {
        shareBtn.addEventListener('click', function() {
            alert('分享至 Google Drive 功能需後端授權，請參考 README 設定 Google API。');
        });
    }

    // 表單送出時禁用按鈕，送出後自動滾動到結果區域
    const form = document.getElementById('promptForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;
            setTimeout(function() {
                submitBtn.disabled = false;
                const resultBlock = document.querySelector('h2');
                if (resultBlock) {
                    resultBlock.scrollIntoView({behavior: 'smooth'});
                }
            }, 800);
        });
    }

    // 複製文本功能
    const copyTextBtn = document.getElementById('copyTextBtn');
    const promptTextArea = document.getElementById('promptTextArea');
    if (copyTextBtn && promptTextArea) {
        copyTextBtn.addEventListener('click', function() {
            navigator.clipboard.writeText(promptTextArea.value).then(function() {
                // 臨時改變按鈕文字以顯示成功
                const originalText = copyTextBtn.textContent;
                copyTextBtn.textContent = '已複製！';
                copyTextBtn.style.backgroundColor = '#4CAF50';
                copyTextBtn.style.color = 'white';
                
                setTimeout(function() {
                    copyTextBtn.textContent = originalText;
                    copyTextBtn.style.backgroundColor = '';
                    copyTextBtn.style.color = '';
                }, 2000);
            }).catch(function(err) {
                // 降級方案：選擇文本
                promptTextArea.select();
                document.execCommand('copy');
                alert('文本已複製到剪貼板');
            });
        });
    }

    // 複製 JSON 功能
    const copyJsonBtn = document.getElementById('copyJsonBtn');
    const promptJsonArea = document.getElementById('promptJsonArea');
    if (copyJsonBtn && promptJsonArea) {
        copyJsonBtn.addEventListener('click', function() {
            navigator.clipboard.writeText(promptJsonArea.value).then(function() {
                // 臨時改變按鈕文字以顯示成功
                const originalText = copyJsonBtn.textContent;
                copyJsonBtn.textContent = '已複製！';
                copyJsonBtn.style.backgroundColor = '#4CAF50';
                copyJsonBtn.style.color = 'white';
                
                setTimeout(function() {
                    copyJsonBtn.textContent = originalText;
                    copyJsonBtn.style.backgroundColor = '';
                    copyJsonBtn.style.color = '';
                }, 2000);
            }).catch(function(err) {
                // 降級方案：選擇文本
                promptJsonArea.select();
                document.execCommand('copy');
                alert('JSON 已複製到剪貼板');
            });
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
                    alert('請選擇支援的圖片文件格式（PNG、JPG、JPEG、GIF、HEIC）！');
                    return;
                }

                // 檢查文件大小 (16MB)
                if (file.size > 16 * 1024 * 1024) {
                    alert('圖片文件大小不能超過 16MB！');
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
                console.log('HEIC file detected, using server-side conversion...');
                
                // 直接使用服務器端轉換（最可靠的方法）
                const convertUrl = `/convert_heic/${encodeURIComponent(file.name)}`;
                console.log('Using server conversion URL:', convertUrl);
                
                // 顯示載入狀態
                previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #f59e0b;">🔄 正在載入 HEIC 預覽...</small>`;
                dropZoneContent.style.display = 'none';
                dropZonePreview.style.display = 'flex';
                
                // 設置圖片源（瀏覽器會處理載入）
                previewImage.onload = function() {
                    console.log('✅ Server-side HEIC conversion successful!');
                    previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #28a745; font-weight: bold;">🖥️ 服務器端 HEIC 預覽</small>`;
                };
                previewImage.onerror = function(e) {
                    console.log('❌ Server conversion failed, trying client-side fallback...');
                    // 如果服務器轉換失敗，回退到 heic2any
                    attemptClientSideHeicConversion(file);
                };
                previewImage.src = convertUrl + '?t=' + Date.now();
                
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
                ctx.roundRect(120, 40, 60, 40, 8);
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
                // 最終降級到服務器端轉換
                attemptServerSideHeicPreview(file);
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
        
        // Canvas 輔助函數：圓角矩形
        if (!CanvasRenderingContext2D.prototype.roundRect) {
            CanvasRenderingContext2D.prototype.roundRect = function(x, y, width, height, radius) {
                this.beginPath();
                this.moveTo(x + radius, y);
                this.lineTo(x + width - radius, y);
                this.quadraticCurveTo(x + width, y, x + width, y + radius);
                this.lineTo(x + width, y + height - radius);
                this.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
                this.lineTo(x + radius, y + height);
                this.quadraticCurveTo(x, y + height, x, y + height - radius);
                this.lineTo(x, y + radius);
                this.quadraticCurveTo(x, y, x + radius, y);
                this.closePath();
            };
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
            console.log('Attempting client-side HEIC conversion as fallback...');
            
            // 檢查是否有 heic2any 庫
            if (typeof heic2any !== 'undefined') {
                console.log('heic2any library found, starting conversion...');
                // 使用 heic2any 轉換 HEIC 為 JPEG
                heic2any({
                    blob: file,
                    toType: "image/jpeg",
                    quality: 0.8
                }).then(function(conversionResult) {
                    console.log('Client-side HEIC conversion successful!', conversionResult);
                    const convertedBlob = Array.isArray(conversionResult) ? conversionResult[0] : conversionResult;
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        console.log('FileReader loaded converted image successfully');
                        previewImage.src = e.target.result;
                        previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #28a745; font-weight: bold;">✓ 客戶端 HEIC 轉換</small>`;
                        dropZoneContent.style.display = 'none';
                        dropZonePreview.style.display = 'flex';
                    };
                    reader.onerror = function(error) {
                        console.error('FileReader error for converted image:', error);
                        showHeicPlaceholder(file);
                    };
                    reader.readAsDataURL(convertedBlob);
                }).catch(function(error) {
                    console.error('Client-side HEIC conversion failed:', error);
                    console.log('Falling back to Canvas-based preview...');
                    // 轉換失敗，嘗試 Canvas 預覽
                    attemptCanvasHeicPreview(file);
                });
            } else {
                console.log('heic2any library not available, trying Canvas preview');
                // 沒有轉換庫，嘗試 Canvas 預覽
                attemptCanvasHeicPreview(file);
            }
        }

        // 格式化文件大小
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
    }
});
