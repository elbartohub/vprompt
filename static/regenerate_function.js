// 重新生成圖片功能
function regenerateFromJson() {
    // prevent double-starts across DOM replacements
    if (window._vprompt_generation_in_progress) {
        showNotification(document.documentElement.getAttribute("data-lang") === "en" ? "Generation already in progress" : "生成進行中", "info");
        return;
    }
    const promptJsonArea = document.getElementById("promptJsonArea");
    const regenerateBtn = document.getElementById("regenerateBtn");

    if (!promptJsonArea || !regenerateBtn) {
        console.error("Required elements not found");
        return;
    }

    const originalText = regenerateBtn.textContent;
    regenerateBtn.disabled = true;
    regenerateBtn.textContent = document.documentElement.getAttribute("data-lang") === "en" ? "🎨 Generating..." : "🎨 生成中...";

    // Validate JSON
    let jsonData;
    try {
        jsonData = JSON.parse(promptJsonArea.value);
    } catch (e) {
        showNotification(document.documentElement.getAttribute("data-lang") === "en" ? "Invalid JSON format. Please check the syntax." : "JSON 格式錯誤，請檢查語法。", "error");
        // Restore UI state
        regenerateBtn.disabled = false;
        regenerateBtn.textContent = originalText;
        window._vprompt_generation_in_progress = false;
        return;
    }

    // mark in-progress so rapid second clicks don't start another job
    window._vprompt_generation_in_progress = true;

    // Create form data for starting background job
    const formData = new FormData();
    formData.append("json_data", JSON.stringify(jsonData));
    
    // Add seed parameter if provided
    const seedInput = document.getElementById("regenerateSeed");
    let currentSeed = null;
    if (seedInput && seedInput.value.trim() !== "") {
        const seedValue = parseInt(seedInput.value.trim());
        if (!isNaN(seedValue) && seedValue >= 0 && seedValue <= 4294967295) {
            formData.append("seed", seedValue.toString());
            currentSeed = seedValue;
            console.log(`Using seed: ${seedValue}`);
        } else {
            showNotification(document.documentElement.getAttribute("data-lang") === "en" 
                ? "Invalid seed value. Please enter a number between 0 and 4294967295." 
                : "種子值無效。請輸入 0 到 4294967295 之間的數字。", "warning");
            // Restore UI state
            regenerateBtn.disabled = false;
            regenerateBtn.textContent = originalText;
            window._vprompt_generation_in_progress = false;
            return;
        }
    } else {
        console.log("Using random seed");
    }

    // Start generation job
    fetch("/start_generation", { method: "POST", body: formData })
        .then(resp => resp.json())
        .then(data => {
            if (data.error) throw new Error(data.error);
            const jobId = data.job_id;
            const seed = data.seed;
            
            // Display the seed that was used
            if (seed !== null && seed !== undefined) {
                displayLastUsedSeed(seed);
            }

            console.log(`[DEBUG] Starting polling for job ${jobId}`);
            
            let resultsFetched = false;

            // Clear any existing intervals
            if (window._vprompt_poll_interval) {
                clearInterval(window._vprompt_poll_interval);
            }

            // Poll for progress
            const poll = setInterval(() => {
                fetch(`/job_status/${jobId}`)
                    .then(async r => {
                        if (!r.ok) {
                            const txt = await r.text().catch(() => "<no-body>");
                            throw new Error(`HTTP ${r.status}: ${txt}`);
                        }
                        const s = await r.json().catch(async (e) => {
                            const txt = await r.text().catch(() => "<no-body>");
                            throw new Error(`Invalid JSON response: ${txt}`);
                        });
                        if (s.error) throw new Error(s.error);
                        // Handle completion
                        if (s.status === "done" && !resultsFetched) {
                            console.log(`[DEBUG] Job ${jobId} completed, fetching results...`);
                            resultsFetched = true;
                            const startGalleryFetch = () => {
                                clearInterval(poll);
                                console.log(`[DEBUG] Starting gallery fetch for job ${jobId}`);
                                
                                // Fetch results
                                fetch(`/regeneration_result/${jobId}`)
                                    .then(response => {
                                        if (!response.ok) {
                                            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                                        }
                                        return response.text();
                                    })
                                    .then(text => {
                                        console.log(`[DEBUG] Successfully fetched results for job ${jobId}`);
                                        // Check if response is JSON (error) or HTML (success)
                                        if (text.trim().startsWith('{') || text.trim().startsWith('[')) {
                                            const jsonResponse = JSON.parse(text);
                                            if (jsonResponse.error) {
                                                throw new Error(jsonResponse.error);
                                            }
                                        }
                                        // Success: update gallery and UI
                                        const jsonSection = promptJsonArea.closest("div");
                                        const existingSections = document.querySelectorAll("h2[data-en*='Generated Images'], h2[data-zh*='生成的圖片']");
                                        existingSections.forEach(section => {
                                            const parentDiv = section.parentElement;
                                            if (parentDiv && parentDiv !== jsonSection.parentElement) {
                                                parentDiv.remove();
                                            }
                                        });
                                        jsonSection.parentNode.insertBefore(
                                            document.createRange().createContextualFragment(text),
                                            jsonSection.nextSibling
                                        );
                                        regenerateBtn.disabled = false;
                                        regenerateBtn.textContent = originalText;
                                        window._vprompt_generation_in_progress = false;
                                        showNotification(
                                            document.documentElement.getAttribute("data-lang") === "en" 
                                                ? "✅ Image regeneration completed successfully!" 
                                                : "✅ 圖片重新生成完成！", 
                                            "success"
                                        );
                                        
                                        // Smooth scroll to generated images
                                        setTimeout(function() {
                                            const generatedImagesHeading = document.querySelector("h2[data-en*='Generated Images'], h2[data-zh*='生成的圖片']");
                                            if (generatedImagesHeading) {
                                                generatedImagesHeading.scrollIntoView({
                                                    behavior: "smooth",
                                                    block: "start"
                                                });
                                            }
                                        }, 100);
                                    })
                                    .catch(error => {
                                        console.error(`[DEBUG] Failed to fetch results for job ${jobId}:`, error);
                                        regenerateBtn.disabled = false;
                                        regenerateBtn.textContent = originalText;
                                        window._vprompt_generation_in_progress = false;
                                        showNotification(
                                            document.documentElement.getAttribute("data-lang") === "en" 
                                                ? "❌ Failed to load generated images" 
                                                : "❌ 無法載入生成的圖片", 
                                            "error"
                                        );
                                    });
                            };
                            
                            startGalleryFetch();
                        } else if (s.status === "error") {
                            clearInterval(poll);
                            showNotification("Generation failed", "error");
                            regenerateBtn.disabled = false;
                            regenerateBtn.textContent = originalText;
                            window._vprompt_generation_in_progress = false;
                        }
                    }).catch(err => {
                        clearInterval(poll);
                        console.error("Polling error:", err);
                        const msg = document.documentElement.getAttribute("data-lang") === "en"
                            ? `Generation polling failed: ${err.message}`
                            : `生成輪詢失敗: ${err.message}`;
                        showNotification(msg, "error");
                        regenerateBtn.disabled = false;
                        regenerateBtn.textContent = originalText;
                        window._vprompt_generation_in_progress = false;
                    });
            }, 500);  // Poll every 0.5 seconds for faster responsiveness
            
            // Store interval reference for cleanup
            window._vprompt_poll_interval = poll;
        })
        .catch(err => {
            console.error("Start job error:", err);
            regenerateBtn.disabled = false;
            regenerateBtn.textContent = originalText;
            window._vprompt_generation_in_progress = false;
        });
}

// Function to update progress in the WebUI
