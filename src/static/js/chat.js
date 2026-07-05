// Muse Spark Explorer Streaming Chat Controller
document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatHistoryContainer = document.getElementById("chat-history");
    
    const tempInput = document.getElementById("chat-temperature");
    const maxTokensInput = document.getElementById("chat-max-tokens");
    const systemPromptInput = document.getElementById("chat-system-prompt");
    
    const clearBtn = document.getElementById("chat-clear");
    const regenerateBtn = document.getElementById("chat-regenerate");
    const tempVal = document.getElementById("temperature-val");
    
    let conversationHistory = [];
    let isGenerating = false;
    let abortController = null;

    // Display temperature slider value dynamically
    if (tempInput && tempVal) {
        tempInput.addEventListener("input", (e) => {
            tempVal.textContent = parseFloat(e.target.value).toFixed(1);
        });
    }

    // Helper: Escape HTML
    function escapeHtml(str) {
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Simple local Markdown parser in case marked.js fails
    function renderMarkdown(text) {
        if (window.marked) {
            try {
                return marked.parse(text);
            } catch (e) {
                console.error("Marked parsing error, fallback to regex: ", e);
            }
        }
        
        // Basic fallback regex markdown formatting (bold, code, lists)
        let html = escapeHtml(text);
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        html = html.replace(/```python([\s\S]*?)```/g, '<pre><code class="language-python">$1</code></pre>');
        html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        html = html.replace(/`(.*?)`/g, '<code>$1</code>');
        html = html.replace(/\n/g, '<br>');
        return html;
    }

    // Auto-scroll to bottom of chat
    function scrollToBottom() {
        chatHistoryContainer.scrollTop = chatHistoryContainer.scrollHeight;
    }

    // Create Toast notification
    function showToast(message, type = "success") {
        const toastContainer = document.getElementById("toast-container");
        if (!toastContainer) return;
        
        const toast = document.createElement("div");
        toast.className = `toast align-items-center text-white bg-${type} border-0 show m-2`;
        toast.setAttribute("role", "alert");
        toast.setAttribute("aria-live", "assertive");
        toast.setAttribute("aria-atomic", "true");
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        toastContainer.appendChild(toast);
        
        // Auto remove toast after 4 seconds
        setTimeout(() => {
            toast.classList.remove("show");
            setTimeout(() => toast.remove(), 500);
        }, 4000);
    }

    // Copy response to clipboard
    window.copyMessageText = function (btn, textBase64) {
        const text = atob(textBase64);
        navigator.clipboard.writeText(text).then(() => {
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<i class="bi bi-check-lg"></i> Copied!';
            showToast("Response copied to clipboard.", "success");
            setTimeout(() => {
                btn.innerHTML = originalHTML;
            }, 2000);
        }).catch(err => {
            showToast("Failed to copy response.", "danger");
        });
    };

    // Render message card to UI
    function displayMessage(role, content, isStreaming = false) {
        const messageDiv = document.createElement("div");
        messageDiv.className = `chat-message ${role}`;
        
        const avatarHTML = role === "user" 
            ? '<i class="bi bi-person-fill"></i>' 
            : '<i class="bi bi-cpu-fill"></i>';
            
        // Encode text to base64 safely for copy button click payload
        const base64Content = btoa(unescape(encodeURIComponent(content)));
        
        const headerHTML = role === "assistant" && !isStreaming
            ? `<div class="d-flex justify-content-end mb-1">
                 <button class="btn btn-sm btn-link text-muted p-0 me-2" onclick="copyMessageText(this, '${base64Content}')" title="Copy to clipboard">
                   <i class="bi bi-clipboard"></i> Copy
                 </button>
               </div>`
            : "";

        messageDiv.innerHTML = `
            <div class="chat-avatar">${avatarHTML}</div>
            <div>
                ${headerHTML}
                <div class="chat-bubble">${renderMarkdown(content)}</div>
            </div>
        `;
        
        chatHistoryContainer.appendChild(messageDiv);
        
        // Apply Prism highlighting
        if (window.Prism && !isStreaming) {
            Prism.highlightAllUnder(messageDiv);
        }
        
        scrollToBottom();
        return messageDiv;
    }

    // Toggle button inputs based on generation states
    function setGeneratingState(generating) {
        isGenerating = generating;
        const submitBtn = chatForm.querySelector("button[type='submit']");
        
        if (generating) {
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';
            submitBtn.setAttribute("disabled", "true");
            if (regenerateBtn) regenerateBtn.setAttribute("disabled", "true");
        } else {
            submitBtn.innerHTML = '<i class="bi bi-send-fill"></i>';
            submitBtn.removeAttribute("disabled");
            if (regenerateBtn && conversationHistory.length >= 2) regenerateBtn.removeAttribute("disabled");
        }
    }

    // Append Typing Indicator
    function showTypingIndicator() {
        const indicator = document.createElement("div");
        indicator.id = "typing-indicator";
        indicator.className = "chat-message assistant";
        indicator.innerHTML = `
            <div class="chat-avatar"><i class="bi bi-cpu-fill"></i></div>
            <div class="chat-bubble">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        chatHistoryContainer.appendChild(indicator);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById("typing-indicator");
        if (indicator) {
            indicator.remove();
        }
    }

    // The Streaming Engine
    async function startChatStream() {
        if (conversationHistory.length === 0) return;
        
        setGeneratingState(true);
        showTypingIndicator();
        
        const temp = parseFloat(tempInput ? tempInput.value : 0.7);
        const maxTokens = parseInt(maxTokensInput ? maxTokensInput.value : 1000);
        const systemPrompt = systemPromptInput ? systemPromptInput.value : "";
        
        // Retrieve CSRF token
        const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfTokenMeta ? csrfTokenMeta.getAttribute("content") : "";

        abortController = new AbortController();

        try {
            const startLatencyTime = performance.now();
            const response = await fetch("/chat/stream", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken
                },
                body: JSON.stringify({
                    messages: conversationHistory,
                    temperature: temp,
                    max_tokens: maxTokens,
                    system_prompt: systemPrompt
                }),
                signal: abortController.signal
            });

            removeTypingIndicator();

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.error || `HTTP error ${response.status}`);
            }

            // Create placeholder assistant message div
            let assistantMessage = "";
            const bubbleDiv = displayMessage("assistant", assistantMessage, true);
            const bubbleContent = bubbleDiv.querySelector(".chat-bubble");
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let partialBuffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const textChunk = decoder.decode(value, { stream: true });
                partialBuffer += textChunk;

                const lines = partialBuffer.split("\n");
                // Save the last partial line (if any) back to the buffer
                partialBuffer = lines.pop();

                for (const line of lines) {
                    const cleanedLine = line.trim();
                    if (!cleanedLine.startsWith("data: ")) continue;

                    const jsonStr = cleanedLine.slice(6).trim();
                    try {
                        const parsed = JSON.parse(jsonStr);
                        
                        if (parsed.error) {
                            throw new Error(parsed.error);
                        }
                        
                        if (parsed.token) {
                            assistantMessage += parsed.token;
                            bubbleContent.innerHTML = renderMarkdown(assistantMessage);
                            scrollToBottom();
                        }
                        
                        if (parsed.done) {
                            // Completed successfully
                            break;
                        }
                    } catch (jsonErr) {
                        // Skip corrupted/partial packets
                        continue;
                    }
                }
            }

            // Record completed assistant message to memory history
            conversationHistory.push({ role: "assistant", content: assistantMessage });
            
            // Re-render final message to inject copy button
            bubbleDiv.remove();
            displayMessage("assistant", assistantMessage);
            
            const endLatencyTime = performance.now();
            const latencySec = ((endLatencyTime - startLatencyTime) / 1000).toFixed(2);
            
            // Display telemetry feedback
            const tokenEstimate = Math.round(assistantMessage.length / 4);
            showToast(`Response streaming completed in ${latencySec}s (Approx ${tokenEstimate} tokens).`, "success");

        } catch (err) {
            removeTypingIndicator();
            if (err.name === "AbortError") {
                showToast("Response streaming cancelled.", "warning");
            } else {
                console.error("Stream reader error: ", err);
                displayMessage("assistant", `*Error: ${err.message || "Failed to receive stream response."}*`);
                showToast("API stream failure occurred.", "danger");
            }
        } finally {
            setGeneratingState(false);
            abortController = null;
        }
    }

    // Submit user message
    if (chatForm) {
        chatForm.addEventListener("submit", (e) => {
            e.preventDefault();
            if (isGenerating) return;

            const text = chatInput.value.trim();
            if (!text) return;

            // Clear input field
            chatInput.value = "";
            
            // Display user message in UI
            displayMessage("user", text);
            
            // Push user message to list
            conversationHistory.push({ role: "user", content: text });
            
            // Run Stream
            startChatStream();
        });

        // Submit message on Enter (but allow Shift+Enter for newline)
        chatInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                chatForm.requestSubmit();
            }
        });
    }

    // Clear history button
    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            if (isGenerating && abortController) {
                abortController.abort();
            }
            conversationHistory = [];
            chatHistoryContainer.innerHTML = `
                <div class="text-center text-muted my-5">
                    <i class="bi bi-chat-left-dots-fill display-4 mb-3 d-block text-accent"></i>
                    <p>Start a new streaming conversation with Muse Spark.</p>
                </div>
            `;
            if (regenerateBtn) regenerateBtn.setAttribute("disabled", "true");
            showToast("Conversation history cleared.", "info");
        });
    }

    // Regenerate last response button
    if (regenerateBtn) {
        regenerateBtn.addEventListener("click", () => {
            if (isGenerating || conversationHistory.length < 2) return;
            
            // Pop the last assistant message
            const lastMessage = conversationHistory[conversationHistory.length - 1];
            if (lastMessage.role === "assistant") {
                conversationHistory.pop();
                
                // Remove the last assistant node from UI
                const assistantNodes = chatHistoryContainer.querySelectorAll(".chat-message.assistant");
                if (assistantNodes.length > 0) {
                    assistantNodes[assistantNodes.length - 1].remove();
                }
                
                // Re-trigger stream
                startChatStream();
            }
        });
    }
});
