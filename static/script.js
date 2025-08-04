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

    // 重設按鈕：清除所有欄位與 cookie
    const resetBtn = document.getElementById('resetBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            // 清除所有欄位
            form.reset();
            // 清除 cookie
            const cookies = document.cookie.split(';');
            for (let c of cookies) {
                const eqPos = c.indexOf('=');
                const name = eqPos > -1 ? c.substr(0, eqPos).trim() : c.trim();
                document.cookie = name + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';
            }
            // 頁面刷新
            window.location.reload();
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

    if (dropZone && fileInput) {
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

        // 移除圖片按鈕
        if (removeImageBtn) {
            removeImageBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                removeImage();
            });
        }

        // 處理文件函數
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
            
            // 檢查是否為 HEIC/HEIF 檔案
            if (fileName.endsWith('.heic') || fileName.endsWith('.heif')) {
                // HEIC 檔案無法在瀏覽器中預覽，直接顯示佔位符
                previewImage.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE1MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjVmNWY1IiBzdHJva2U9IiNkZGQiIHN0cm9rZS13aWR0aD0iMiIgcng9IjgiLz48Y2lyY2xlIGN4PSI1MCIgY3k9IjUwIiByPSIxOCIgZmlsbD0iIzRDQUY1MCIvPjx0ZXh0IHg9IjUwIiB5PSI1NiIgZm9udC1mYW1pbHk9IkFyaWFsLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjEyIiBmaWxsPSJ3aGl0ZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC13ZWlnaHQ9ImJvbGQiPkhFSUM8L3RleHQ+PHRleHQgeD0iMTAwIiB5PSI5MCIgZm9udC1mYW1pbHk9IkFyaWFsLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjE0IiBmaWxsPSIjNjY2IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj7lt7LkuIrlgrPnmoQ8L3RleHQ+PHRleHQgeD0iMTAwIiB5PSIxMTAiIGZvbnQtZmFtaWx5PSJBcmlhbCwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+6Ieq5YuV5LiK5YKz5oiQ5YqfPC90ZXh0Pjwvc3ZnPg==';
                previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #4CAF50; font-weight: bold;">✓ HEIC 格式已就緒，將正常處理</small>`;
                
                // 直接顯示預覽，不需要 FileReader
                dropZoneContent.style.display = 'none';
                dropZonePreview.style.display = 'flex';
            } else {
                // 一般圖片檔案使用 FileReader 正常預覽
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewImage.src = e.target.result;
                    previewInfo.textContent = `${file.name} (${formatFileSize(file.size)})`;
                    dropZoneContent.style.display = 'none';
                    dropZonePreview.style.display = 'flex';
                };
                reader.onerror = function() {
                    // 如果 FileReader 失敗，也使用佔位符
                    previewImage.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE1MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjVmNWY1IiBzdHJva2U9IiNkZGQiIHN0cm9rZS13aWR0aD0iMiIgcng9IjgiLz48dGV4dCB4PSIxMDAiIHk9Ijc1IiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM2NjYiIHRleHQtYW5jaG9yPSJtaWRkbGUiPuWcluePh+aqlOahiDwvdGV4dD48dGV4dCB4PSIxMDAiIHk9Ijk1IiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiPuaaguaXtueFoOazlemgkOimi+mihzwvdGV4dD48L3N2Zz4=';
                    previewInfo.innerHTML = `${file.name} (${formatFileSize(file.size)})<br><small style="color: #ff9800;">⚠ 預覽不可用，但檔案已就緒</small>`;
                    dropZoneContent.style.display = 'none';
                    dropZonePreview.style.display = 'flex';
                };
                reader.readAsDataURL(file);
            }
        }

        // 移除圖片函數
        function removeImage() {
            fileInput.value = '';
            previewImage.src = '';
            previewInfo.textContent = '';
            dropZoneContent.style.display = 'block';
            dropZonePreview.style.display = 'none';
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
