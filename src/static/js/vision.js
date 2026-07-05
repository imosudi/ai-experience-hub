// Muse Spark Explorer Computer Vision JavaScript Controller
document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const selectFileBtn = document.getElementById("select-file-btn");
    
    const previewContainer = document.getElementById("preview-container");
    const previewImage = document.getElementById("preview-image");
    
    const uploadForm = document.getElementById("upload-form");
    const progressContainer = document.getElementById("progress-container");
    const progressBar = document.getElementById("progress-bar");
    
    const resultsCard = document.getElementById("results-card");
    const resultDescription = document.getElementById("result-description");
    const resultSummary = document.getElementById("result-summary");
    const resultConfidence = document.getElementById("result-confidence");
    const resultOcr = document.getElementById("result-ocr");
    const resultObjectsTable = document.getElementById("result-objects-table");
    
    const metaFilename = document.getElementById("meta-filename");
    const metaSize = document.getElementById("meta-size");
    const metaResolution = document.getElementById("meta-resolution");
    const metaFormat = document.getElementById("meta-format");
    const metaLatency = document.getElementById("meta-latency");

    // Click triggers hidden input
    if (selectFileBtn && fileInput) {
        selectFileBtn.addEventListener("click", () => {
            fileInput.click();
        });
    }

    // Drag-over styling
    if (dropZone) {
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
            }, false);
        });

        // Drop file handler
        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                handleImageSelection(files[0]);
            }
        });
    }

    // Input file select handler
    if (fileInput) {
        fileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                handleImageSelection(e.target.files[0]);
            }
        });
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

    // Validate and load image preview
    function handleImageSelection(file) {
        // Clear results
        if (resultsCard) resultsCard.classList.add("d-none");
        
        // Size validation: 5MB limit
        const MAX_SIZE = 5 * 1024 * 1024;
        if (file.size > MAX_SIZE) {
            showToast("File is too large. Maximum allowed size is 5MB.", "danger");
            return;
        }

        // Extension validation
        const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
        if (!allowedTypes.includes(file.type)) {
            showToast("Unsupported file format. Please upload a JPG, PNG, or WEBP image.", "danger");
            return;
        }

        // Render preview image
        const reader = new FileReader();
        reader.onload = (e) => {
            if (previewImage) previewImage.src = e.target.result;
            if (previewContainer) previewContainer.classList.remove("d-none");
        };
        reader.readAsDataURL(file);

        // Upload directly
        uploadImageFile(file);
    }

    // Ajax Image Upload via Fetch
    async function uploadImageFile(file) {
        if (progressContainer) progressContainer.classList.remove("d-none");
        if (progressBar) {
            progressBar.style.width = "20%";
            progressBar.setAttribute("aria-valuenow", "20");
        }

        const formData = new FormData();
        formData.append("file", file);

        const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfTokenMeta ? csrfTokenMeta.getAttribute("content") : "";

        try {
            if (progressBar) {
                progressBar.style.width = "50%";
                progressBar.setAttribute("aria-valuenow", "50");
            }

            const response = await fetch("/vision/upload", {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken
                },
                body: formData
            });

            if (progressBar) {
                progressBar.style.width = "90%";
                progressBar.setAttribute("aria-valuenow", "90");
            }

            const result = await response.json();
            
            if (progressBar) {
                progressBar.style.width = "100%";
                progressBar.setAttribute("aria-valuenow", "100");
            }

            if (!response.ok) {
                throw new Error(result.error || `HTTP error ${response.status}`);
            }

            showToast("Vision analysis completed successfully.", "success");
            renderVisionResults(result);

        } catch (err) {
            console.error("Vision upload failed: ", err);
            showToast(err.message || "Failed to analyze image.", "danger");
            if (previewContainer) previewContainer.classList.add("d-none");
        } finally {
            setTimeout(() => {
                if (progressContainer) progressContainer.classList.add("d-none");
            }, 500);
        }
    }

    // Render output results into tables and metadata boxes
    function renderVisionResults(data) {
        if (!resultsCard) return;

        // Render textual values
        if (resultDescription) resultDescription.textContent = data.description || "No description generated.";
        if (resultSummary) resultSummary.textContent = data.scene_summary || "No summary available.";
        if (resultConfidence) {
            const pct = Math.round((data.confidence_score || 0.0) * 100);
            resultConfidence.innerHTML = `<span class="badge bg-success font-monospace">${pct}%</span>`;
        }
        
        // OCR text
        if (resultOcr) {
            if (data.ocr_text && data.ocr_text.trim()) {
                resultOcr.innerHTML = `<pre class="mb-0 bg-dark p-3 rounded font-monospace">${escapeHtml(data.ocr_text)}</pre>`;
            } else {
                resultOcr.innerHTML = '<span class="text-muted">No text elements detected in image.</span>';
            }
        }

        // Render detected objects
        if (resultObjectsTable) {
            resultObjectsTable.innerHTML = "";
            const objects = data.detected_objects || [];
            
            if (objects.length > 0) {
                objects.forEach(obj => {
                    const row = document.createElement("tr");
                    const confidencePct = Math.round((obj.confidence || 0.0) * 100);
                    
                    row.innerHTML = `
                        <td class="fw-semibold">${escapeHtml(obj.label)}</td>
                        <td>
                            <div class="d-flex align-items-center gap-2">
                                <div class="progress flex-grow-1" style="height: 6px;">
                                    <div class="progress-bar bg-accent" role="progressbar" style="width: ${confidencePct}%" aria-valuenow="${confidencePct}" aria-valuemin="0" aria-valuemax="100"></div>
                                </div>
                                <span class="font-monospace text-muted small">${confidencePct}%</span>
                            </div>
                        </td>
                    `;
                    resultObjectsTable.appendChild(row);
                });
            } else {
                resultObjectsTable.innerHTML = '<tr><td colspan="2" class="text-center text-muted">No objects detected.</td></tr>';
            }
        }

        // Render Metadata Badges
        const meta = data.metadata || {};
        if (metaFilename) metaFilename.textContent = meta.filename || "N/A";
        if (metaSize) metaSize.textContent = meta.size_formatted || "N/A";
        if (metaResolution) metaResolution.textContent = meta.width && meta.height ? `${meta.width} x ${meta.height}` : "N/A";
        if (metaFormat) metaFormat.textContent = meta.format || "N/A";
        if (metaLatency) metaLatency.textContent = data.latency_sec ? `${data.latency_sec.toFixed(2)}s` : "0.00s";

        // Display Card
        resultsCard.classList.remove("d-none");
        
        // Scroll to card
        resultsCard.scrollIntoView({ behavior: "smooth", block: "start" });
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
