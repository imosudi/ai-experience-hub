// Muse Spark Explorer AI Agent (Webpage Summarizer) JavaScript Controller
document.addEventListener("DOMContentLoaded", () => {
    const agentForm = document.getElementById("agent-form");
    const urlInput = document.getElementById("url-input");
    const runBtn = document.getElementById("run-btn");
    
    const resultsContainer = document.getElementById("agent-results");
    const loadingContainer = document.getElementById("agent-loading");
    const placeholderContainer = document.getElementById("agent-placeholder");
    
    const metaTitle = document.getElementById("agent-meta-title");
    const metaUrl = document.getElementById("agent-meta-url");
    const metaWords = document.getElementById("agent-meta-words");
    const metaReadTime = document.getElementById("agent-meta-readtime");
    const metaLatency = document.getElementById("agent-meta-latency");
    
    const summaryBlock = document.getElementById("agent-summary-block");
    const keyPointsBlock = document.getElementById("agent-keypoints-block");
    const actionItemsBlock = document.getElementById("agent-actionitems-block");

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

    // Basic URL Regex Validator
    function isValidUrl(string) {
        try {
            const url = new URL(string);
            return url.protocol === "http:" || url.protocol === "https:";
        } catch (_) {
            return false;  
        }
    }

    if (agentForm) {
        agentForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            let urlVal = urlInput.value.trim();
            if (!urlVal) {
                showToast("Please enter a webpage URL.", "warning");
                return;
            }

            // Standardize URL schema if missing
            if (!/^https?:\/\//i.test(urlVal)) {
                urlVal = "http://" + urlVal;
                urlInput.value = urlVal;
            }

            if (!isValidUrl(urlVal)) {
                showToast("Please enter a valid HTTP/HTTPS URL format.", "danger");
                return;
            }

            // Setup loading UI
            if (placeholderContainer) placeholderContainer.classList.add("d-none");
            if (resultsContainer) resultsContainer.classList.add("d-none");
            if (loadingContainer) loadingContainer.classList.remove("d-none");
            
            runBtn.setAttribute("disabled", "true");
            runBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Processing page...';

            const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
            const csrfToken = csrfTokenMeta ? csrfTokenMeta.getAttribute("content") : "";

            try {
                const response = await fetch("/agent/run", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken
                    },
                    body: JSON.stringify({ url: urlVal })
                });

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.error || `HTTP error ${response.status}`);
                }

                // Render Results
                if (metaTitle) metaTitle.textContent = result.title;
                if (metaUrl) {
                    metaUrl.textContent = result.url;
                    metaUrl.href = result.url;
                }
                if (metaWords) metaWords.textContent = `${result.word_count} words`;
                if (metaReadTime) metaReadTime.textContent = `~${result.reading_time} min read`;
                if (metaLatency) metaLatency.latency_sec = result.latency_sec ? `${result.latency_sec.toFixed(2)}s` : "0.00s";

                // Format Markdown content to HTML
                if (summaryBlock) {
                    summaryBlock.textContent = result.summary;
                }
                
                if (keyPointsBlock) {
                    // Split key points by line breaks to render as nice bullets
                    const lines = result.key_points.split("\n");
                    keyPointsBlock.innerHTML = "";
                    lines.forEach(l => {
                        const cleanLine = l.trim().replace(/^-\s*/, "");
                        if (cleanLine) {
                            const li = document.createElement("li");
                            li.className = "mb-2";
                            li.textContent = cleanLine;
                            keyPointsBlock.appendChild(li);
                        }
                    });
                }
                
                if (actionItemsBlock) {
                    const lines = result.action_items.split("\n");
                    actionItemsBlock.innerHTML = "";
                    lines.forEach(l => {
                        const cleanLine = l.trim().replace(/^-\s*/, "");
                        if (cleanLine) {
                            const li = document.createElement("li");
                            li.className = "mb-2 fw-semibold";
                            li.innerHTML = `<i class="bi bi-check2-circle text-success me-2"></i> ${escapeHtml(cleanLine)}`;
                            actionItemsBlock.appendChild(li);
                        }
                    });
                }

                if (loadingContainer) loadingContainer.classList.add("d-none");
                if (resultsContainer) resultsContainer.classList.remove("d-none");
                
                showToast("Webpage summarization completed successfully.", "success");

            } catch (err) {
                console.error("AI Agent run failed: ", err);
                showToast(err.message || "Failed to process webpage.", "danger");
                
                if (loadingContainer) loadingContainer.classList.add("d-none");
                if (placeholderContainer) placeholderContainer.classList.remove("d-none");
            } finally {
                runBtn.removeAttribute("disabled");
                runBtn.innerHTML = '<i class="bi bi-play-fill"></i> Run Agent';
            }
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
});
