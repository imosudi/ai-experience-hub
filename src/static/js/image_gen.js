// Muse Spark Explorer Image Generation JavaScript Controller
document.addEventListener("DOMContentLoaded", () => {
    const genForm = document.getElementById("gen-form");
    const generateBtn = document.getElementById("generate-btn");
    
    const promptInput = document.getElementById("prompt-input");
    const negPromptInput = document.getElementById("neg-prompt-input");
    
    const sizeSelect = document.getElementById("size-select");
    const qualitySelect = document.getElementById("quality-select");
    const styleSelect = document.getElementById("style-select");
    const seedInput = document.getElementById("seed-input");
    
    const imageCanvas = document.getElementById("image-canvas");
    const canvasImage = document.getElementById("canvas-image");
    const canvasLoader = document.getElementById("canvas-loader");
    const canvasPlaceholder = document.getElementById("canvas-placeholder");
    
    const downloadBtn = document.getElementById("download-btn");
    const metaPrompt = document.getElementById("meta-prompt");
    const metaSeed = document.getElementById("meta-seed");
    const metaStyle = document.getElementById("meta-style");
    const metaLatency = document.getElementById("meta-latency");
    
    const historyContainer = document.getElementById("gen-history-list");
    
    let imageHistory = [];

    // Load history from localStorage
    function loadHistory() {
        const cached = localStorage.getItem("muse_image_history");
        if (cached) {
            try {
                imageHistory = JSON.parse(cached);
            } catch (e) {
                imageHistory = [];
            }
        }
        renderHistoryList();
    }

    function saveHistory() {
        localStorage.setItem("muse_image_history", JSON.stringify(imageHistory));
    }

    function showToast(message, type = "success") {
        const toastContainer = document.getElementById("toast-container");
        if (!toastContainer) return;
        
        const toast = document.createElement("div");
        toast.className = `toast align-items-center text-white bg-${type} border-0 show m-2`;
        toast.setAttribute("role", "alert");
        toastContainer.appendChild(toast);
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        setTimeout(() => {
            toast.classList.remove("show");
            setTimeout(() => toast.remove(), 500);
        }, 4000);
    }

    // Render local generation history cards
    function renderHistoryList() {
        if (!historyContainer) return;
        historyContainer.innerHTML = "";

        if (imageHistory.length === 0) {
            historyContainer.innerHTML = `
                <div class="col-12 text-center text-muted py-4">
                    <p>No recently generated images in local cache.</p>
                </div>
            `;
            return;
        }

        imageHistory.forEach((item, index) => {
            const cardCol = document.createElement("div");
            cardCol.className = "col-md-4 col-sm-6 mb-3";
            cardCol.innerHTML = `
                <div class="card glass-card h-100 overflow-hidden">
                    <div class="position-relative ratio ratio-1x1 bg-dark">
                        <img src="${item.url}" class="card-img-top object-fit-cover" alt="${escapeHtml(item.prompt)}">
                    </div>
                    <div class="card-body p-3">
                        <p class="card-text text-truncate fw-semibold mb-1" title="${escapeHtml(item.prompt)}">${escapeHtml(item.prompt)}</p>
                        <div class="d-flex justify-content-between align-items-center mt-2">
                            <span class="badge bg-secondary font-monospace">${item.style}</span>
                            <a href="${item.url}" download="${item.filename}" class="btn btn-sm btn-outline-accent">
                                <i class="bi bi-download"></i>
                            </a>
                        </div>
                    </div>
                </div>
            `;
            historyContainer.appendChild(cardCol);
        });
    }

    function escapeHtml(str) {
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Submit handler
    if (genForm) {
        genForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            const prompt = promptInput.value.trim();
            if (!prompt) {
                showToast("Please enter a prompt.", "warning");
                return;
            }

            // Set Loading UI
            if (canvasPlaceholder) canvasPlaceholder.classList.add("d-none");
            if (canvasImage) canvasImage.classList.add("d-none");
            if (canvasLoader) canvasLoader.classList.remove("d-none");
            
            generateBtn.setAttribute("disabled", "true");
            generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Generating...';

            const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
            const csrfToken = csrfTokenMeta ? csrfTokenMeta.getAttribute("content") : "";

            const payload = {
                prompt: prompt,
                negative_prompt: negPromptInput ? negPromptInput.value.trim() : "",
                size: sizeSelect ? sizeSelect.value : "512x512",
                quality: qualitySelect ? qualitySelect.value : "standard",
                style: styleSelect ? styleSelect.value : "photorealistic",
                seed: seedInput ? seedInput.value.trim() : null
            };

            try {
                const response = await fetch("/image-gen/generate", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken
                    },
                    body: JSON.stringify(payload)
                });

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.error || `HTTP error ${response.status}`);
                }

                // Render Canvas Image
                if (canvasImage) {
                    canvasImage.src = result.url;
                    canvasImage.onload = () => {
                        if (canvasLoader) canvasLoader.classList.add("d-none");
                        canvasImage.classList.remove("d-none");
                    };
                }

                // Render Canvas Telemetry Meta
                if (downloadBtn) {
                    downloadBtn.href = result.url;
                    downloadBtn.setAttribute("download", result.filename);
                    downloadBtn.classList.remove("disabled");
                }
                
                if (metaPrompt) metaPrompt.textContent = result.prompt;
                if (metaSeed) metaSeed.textContent = result.seed;
                if (metaStyle) metaStyle.textContent = result.style;
                if (metaLatency) metaLatency.textContent = `${result.latency_sec.toFixed(2)}s`;

                // Add to history list
                imageHistory.unshift({
                    url: result.url,
                    filename: result.filename,
                    prompt: result.prompt,
                    style: result.style
                });
                
                // Limit cached history to 12 items
                imageHistory = imageHistory.slice(0, 12);
                saveHistory();
                renderHistoryList();
                
                showToast("Image generated successfully.", "success");

            } catch (err) {
                console.error("Image generation failed: ", err);
                showToast(err.message || "Failed to generate image.", "danger");
                
                // Re-enable placeholder if generation fails
                if (canvasLoader) canvasLoader.classList.add("d-none");
                if (canvasPlaceholder) canvasPlaceholder.classList.remove("d-none");
            } finally {
                generateBtn.removeAttribute("disabled");
                generateBtn.innerHTML = '<i class="bi bi-magic"></i> Generate Spark';
            }
        });
    }

    // Initialize Page
    loadHistory();
});
