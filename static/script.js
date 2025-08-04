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
                
                // 檢查文件類型
                if (!file.type.startsWith('image/')) {
                    alert('請選擇圖片文件！');
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
            const reader = new FileReader();
            reader.onload = function(e) {
                previewImage.src = e.target.result;
                previewInfo.textContent = `${file.name} (${formatFileSize(file.size)})`;
                dropZoneContent.style.display = 'none';
                dropZonePreview.style.display = 'flex';
            };
            reader.readAsDataURL(file);
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
