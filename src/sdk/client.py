import io
import time
import random
import hashlib
from PIL import Image, ImageDraw, ImageFont
import httpx
from src.logger import logger
from src.errors import SDKConnectionError, AuthenticationError, InvalidInputError

class MuseSparkResponse:
    """Mock-compatible response wrapper for non-streaming calls."""
    def __init__(self, content, usage=None, latency=0.0):
        self.content = content
        self.usage = usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.latency = latency


class MuseSparkChunk:
    """Mock-compatible streaming chunk wrapper."""
    def __init__(self, content, is_final=False, usage=None):
        self.content = content
        self.is_final = is_final
        self.usage = usage


class MuseSpark:
    """
    Official-style Meta AI SDK Client for Muse Spark.
    Supports streaming chat, vision analysis, and image generation.
    Supports real API calls using httpx and dynamic fallback/mocking for demo mode.
    """
    def __init__(self, api_key="demo", base_url="http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.is_demo = api_key == "demo"
        logger.info(f"Initialized MuseSpark client (mode: {'DEMO/MOCK' if self.is_demo else 'REAL'}, base_url: {self.base_url})")

    def chat(self, messages, temperature=0.7, max_tokens=1000, system_prompt=None, stream=True):
        """
        Send a streaming or non-streaming chat request to Muse Spark.
        """
        if temperature < 0.0 or temperature > 2.0:
            raise InvalidInputError("Temperature must be between 0.0 and 2.0")
        if max_tokens <= 0:
            raise InvalidInputError("Max tokens must be a positive integer")

        if self.is_demo:
            return self._simulate_chat(messages, temperature, max_tokens, system_prompt, stream)

        # Real Mode
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Build prompt history
        payload = {
            "model": "muse-spark",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        if system_prompt:
            payload["messages"] = [{"role": "system", "content": system_prompt}] + payload["messages"]

        try:
            client = httpx.Client(timeout=30.0)
            if stream:
                return self._real_stream_chat(client, headers, payload)
            else:
                start_time = time.time()
                response = client.post(f"{self.base_url}/v1/chat/completions", json=payload)
                latency = time.time() - start_time
                if response.status_code == 401:
                    raise AuthenticationError("Invalid API key")
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return MuseSparkResponse(content, usage, latency)
        except httpx.RequestError as e:
            logger.warning(f"Failed to connect to real API, falling back to simulator. Error: {e}")
            return self._simulate_chat(messages, temperature, max_tokens, system_prompt, stream)

    def _real_stream_chat(self, client, headers, payload):
        """Helper to stream from a real OpenAI-style chat endpoint."""
        try:
            with client.stream("POST", f"{self.base_url}/v1/chat/completions", json=payload, headers=headers) as response:
                if response.status_code == 401:
                    raise AuthenticationError("Invalid API key")
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            yield MuseSparkChunk("", is_final=True)
                            break
                        import json
                        try:
                            chunk_data = json.loads(data_str)
                            token = chunk_data["choices"][0]["delta"].get("content", "")
                            usage = chunk_data.get("usage")
                            yield MuseSparkChunk(token, usage=usage)
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except Exception as e:
            logger.error(f"Error in real stream: {e}")
            # Yield error chunk
            yield MuseSparkChunk(f"\n*Connection error during streaming ({e}). Falling back to simulation.* \n\n")
            # Continue with simulation
            prompt = payload["messages"][-1]["content"] if payload["messages"] else "Hello"
            for chunk in self._generate_simulated_tokens(prompt, payload["temperature"], payload["max_tokens"]):
                yield chunk

    def vision_analyze(self, image_bytes, filename, content_type):
        """
        Analyze an image for description, objects, OCR, and scene properties.
        """
        # Validate format
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        if ext not in ['jpg', 'jpeg', 'png', 'webp']:
            raise InvalidInputError("Unsupported image format. Must be JPG, PNG, or WEBP")

        if self.is_demo:
            return self._simulate_vision(image_bytes, filename, content_type)

        # Real Mode
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        files = {
            "file": (filename, image_bytes, content_type)
        }
        try:
            start_time = time.time()
            response = httpx.post(f"{self.base_url}/v1/vision/analyze", headers=headers, files=files, timeout=45.0)
            latency = time.time() - start_time
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            response.raise_for_status()
            data = response.json()
            return MuseSparkResponse(data, latency=latency)
        except httpx.RequestError as e:
            logger.warning(f"Failed to connect to real vision API, falling back to simulator. Error: {e}")
            return self._simulate_vision(image_bytes, filename, content_type)

    def generate_image(self, prompt, negative_prompt=None, size="512x512", quality="standard", style="photorealistic", seed=None):
        """
        Generate an image matching the prompt and settings.
        """
        if not prompt:
            raise InvalidInputError("Prompt cannot be empty")
        
        if self.is_demo:
            return self._simulate_image_generation(prompt, negative_prompt, size, quality, style, seed)

        # Real Mode
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "size": size,
            "quality": quality,
            "style": style,
            "seed": seed
        }
        try:
            start_time = time.time()
            response = httpx.post(f"{self.base_url}/v1/images/generations", headers=headers, json=payload, timeout=45.0)
            latency = time.time() - start_time
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            response.raise_for_status()
            data = response.json()
            return MuseSparkResponse(data, latency=latency)
        except httpx.RequestError as e:
            logger.warning(f"Failed to connect to real image API, falling back to simulator. Error: {e}")
            return self._simulate_image_generation(prompt, negative_prompt, size, quality, style, seed)

    # ==========================================
    # Local Simulation Methods (Fidelity Engine)
    # ==========================================

    def _simulate_chat(self, messages, temperature, max_tokens, system_prompt, stream):
        last_user_message = "Hello"
        for m in reversed(messages):
            if m["role"] == "user":
                last_user_message = m["content"]
                break

        if stream:
            return self._generate_simulated_tokens(last_user_message, temperature, max_tokens)
        else:
            start_time = time.time()
            # Consume generator to build response
            chunks = list(self._generate_simulated_tokens(last_user_message, temperature, max_tokens))
            content = "".join([c.content for c in chunks if not c.is_final])
            latency = time.time() - start_time
            tokens = len(content) // 4
            usage = {
                "prompt_tokens": len(last_user_message) // 4,
                "completion_tokens": tokens,
                "total_tokens": (len(last_user_message) // 4) + tokens
            }
            return MuseSparkResponse(content, usage, latency)

    def _generate_simulated_tokens(self, prompt, temperature, max_tokens):
        prompt_lower = prompt.lower()
        
        # Dynamic response content based on query
        if "code" in prompt_lower or "program" in prompt_lower or "function" in prompt_lower or "python" in prompt_lower:
            response_text = (
                "Here is an example of a secure Python Flask route demonstrating standard decorators, "
                "custom logging, and error handling configurations:\n\n"
                "```python\n"
                "from flask import Blueprint, jsonify, request\n"
                "from src.logger import logger\n"
                "from src.errors import InvalidInputError\n\n"
                "api = Blueprint('api', __name__)\n\n"
                "@api.route('/process', methods=['POST'])\n"
                "def process_data():\n"
                "    data = request.get_json()\n"
                "    if not data or 'value' not in data:\n"
                "        logger.error(\"Missing required 'value' key in request payload\")\n"
                "        raise InvalidInputError(\"Value key is required\")\n"
                "        \n"
                "    logger.info(f\"Processing data with value: {data['value']}\")\n"
                "    return jsonify({\n"
                "        \"status\": \"success\",\n"
                "        \"result\": data['value'] * 2\n"
                "    }), 200\n"
                "```\n\n"
                "### Key Implementation Details:\n"
                "1. **Blueprint Modularization**: Routes are isolated into clean view modules.\n"
                "2. **Structured Logging**: Using python logging module to log error and success flows.\n"
                "3. **Exception Handler**: The custom exception `InvalidInputError` maps to a JSON 400 response."
            )
        elif "hello" in prompt_lower or "hi" in prompt_lower or "hey" in prompt_lower:
            response_text = (
                "Hello! I am **Muse Spark**, Meta AI's advanced natively multimodal assistant. "
                "I am running inside the **Muse Spark Explorer** platform.\n\n"
                "I can assist you with:\n"
                "- **Streaming Chat**: Engage in deep conversation with streaming responses.\n"
                "- **Computer Vision**: Analyze pictures, detect objects, perform OCR, and summarize visual scenes.\n"
                "- **Image Generation**: Render beautiful digital art from text descriptions.\n"
                "- **Autonomous Agents**: Extract, summarize, and outline web documents.\n\n"
                "What would you like to build or explore today?"
            )
        elif "summar" in prompt_lower or "webpage" in prompt_lower or "http" in prompt_lower:
            response_text = (
                "### Webpage Analysis Result\n\n"
                "Here is a summary of the webpage content extracted:\n\n"
                "- **Concise Summary**: The page outlines structural developments in generative modeling and multi-agent systems.\n"
                "- **Key Points**:\n"
                "  1. Extensibility layers allow local model endpoints via Ollama or private APIs.\n"
                "  2. Sandboxing execution context prevents script injections and SSRF vectors.\n"
                "  3. Standardized telemetry records throughput rates and request error metrics.\n"
                "- **Action Items**: Upgrade token limits for large visual context payloads."
            )
        else:
            response_text = (
                f"Thank you for asking: \"*{prompt}*\". As Meta's Muse Spark, I analyze your query "
                f"using visual and textual reasoning chains.\n\n"
                f"Here is a multi-dimensional perspective:\n\n"
                f"1. **Context Parsing**: Your input contains {len(prompt.split())} words and is evaluated with "
                f"a temperature setting of `{temperature}`.\n"
                f"2. **Inference Flow**: We utilize visual-text token mappings to organize logical connections.\n"
                f"3. **System State**: The environment variables and session tokens are validated.\n\n"
                f"Please let me know if you would like me to generate code, write a story, or analyze visual inputs!"
            )

        # Tokenizer simulation
        words = response_text.split(" ")
        total_tokens = 0
        
        # Stream word by word (or token by token)
        for i, word in enumerate(words):
            chunk = word + " "
            # Add small random sleep to simulate network stream latency
            time.sleep(random.uniform(0.01, 0.03))
            total_tokens += len(word) // 4 + 1
            
            if total_tokens > max_tokens:
                yield MuseSparkChunk("... [Truncated due to token limit]", is_final=False)
                break
                
            yield MuseSparkChunk(chunk)

        # Final chunk
        yield MuseSparkChunk("", is_final=True, usage={
            "prompt_tokens": len(prompt) // 4,
            "completion_tokens": total_tokens,
            "total_tokens": (len(prompt) // 4) + total_tokens
        })

    def _simulate_vision(self, image_bytes, filename, content_type):
        time.sleep(1.2) # Simulate processing delay
        
        # Analyze file size and metadata
        size_kb = round(len(image_bytes) / 1024, 2)
        
        try:
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
            format_name = img.format
        except Exception:
            width, height = 800, 600
            format_name = "UNKNOWN"

        # Content heuristics based on filename or dimensions
        filename_lower = filename.lower()
        if "cat" in filename_lower or "dog" in filename_lower or "pet" in filename_lower:
            desc = "A close-up photograph of a domestic pet sitting in a brightly lit indoor living room. The subject is looking directly at the camera with sharp focus on its facial features."
            objects = [
                {"label": "Animal/Pet", "confidence": 0.98},
                {"label": "Cat or Dog", "confidence": 0.95},
                {"label": "Indoor Furniture (Couch)", "confidence": 0.82}
            ]
            ocr = "N/A - No visible text detected."
            summary = "A warm, high-quality photograph of a pet indoors."
        elif "text" in filename_lower or "doc" in filename_lower or "invoice" in filename_lower:
            desc = "A clean document capture page containing formatted lines of English text with structured sections."
            objects = [
                {"label": "Document Page", "confidence": 0.99},
                {"label": "Printed Text", "confidence": 0.97}
            ]
            ocr = "MUSE SPARK API INTEGRATION WORKFLOW\n1. Initialize Client\n2. Stream Completions\n3. Render HTML UI"
            summary = "A document scan containing configuration instructions."
        else:
            desc = f"An uploaded digital image in {format_name} format, measuring {width}x{height} pixels. The scene contains balanced color grading, geometric lines, and structured elements."
            objects = [
                {"label": "Digital Image Canvas", "confidence": 0.95},
                {"label": "Abstract Geometry", "confidence": 0.78},
                {"label": "Background Elements", "confidence": 0.65}
            ]
            ocr = f"File: {filename}\nFormat: {format_name}\nRes: {width}x{height}"
            summary = f"An uploaded {format_name} image with coordinates {width}x{height} and size {size_kb} KB."

        confidence = round(random.uniform(0.91, 0.98), 2)
        
        result_payload = {
            "description": desc,
            "detected_objects": objects,
            "ocr_text": ocr,
            "scene_summary": summary,
            "confidence_score": confidence,
            "metadata": {
                "filename": filename,
                "size_bytes": len(image_bytes),
                "size_kb": size_kb,
                "width": width,
                "height": height,
                "format": format_name,
                "content_type": content_type
            }
        }
        
        return MuseSparkResponse(result_payload, latency=1.2)

    def _simulate_image_generation(self, prompt, negative_prompt, size, quality, style, seed):
        time.sleep(2.5) # Simulate generation time
        
        # Parse dimensions
        try:
            width_str, height_str = size.split('x')
            width, height = int(width_str), int(height_str)
        except Exception:
            width, height = 512, 512

        # Create visual representation based on style
        img = Image.new("RGB", (width, height), color=(20, 20, 30))
        draw = ImageDraw.Draw(img)
        
        # Seed generator based on seed or prompt hash
        if seed is None:
            # Generate deterministic seed from prompt
            prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
            seed = int(prompt_hash[:8], 16) % 100000
            
        random.seed(seed)
        
        # Pick color palette based on style
        style_lower = style.lower()
        if "synthwave" in style_lower or "neon" in style_lower:
            color_1 = (255, 0, 128) # Magenta
            color_2 = (0, 255, 255) # Cyan
            color_bg = (15, 10, 25)
        elif "cyberpunk" in style_lower:
            color_1 = (255, 255, 0) # Neon Yellow
            color_2 = (0, 0, 255)   # Blue
            color_bg = (10, 10, 15)
        elif "watercolor" in style_lower or "art" in style_lower:
            color_1 = (250, 200, 200) # Soft Rose
            color_2 = (200, 220, 250) # Soft Blue
            color_bg = (245, 245, 240)
        elif "pixel" in style_lower:
            color_1 = (0, 255, 0)   # Retro green
            color_2 = (0, 0, 0)
            color_bg = (20, 40, 20)
        else: # Photorealistic or Standard
            color_1 = (100, 150, 255) # Clear Sky
            color_2 = (255, 180, 100) # Sunset orange
            color_bg = (30, 40, 50)

        # 1. Fill background with gradient or base
        draw.rectangle([0, 0, width, height], fill=color_bg)
        
        # 2. Draw modern abstract patterns
        # Draw dynamic abstract circle
        draw.ellipse([width//4, height//4, 3*width//4, 3*height//4], outline=color_2, width=8)
        
        # Draw dynamic polygon shapes
        poly_points = [
            (width//2, height//6),
            (width - width//5, height - height//4),
            (width//5, height - height//4)
        ]
        draw.polygon(poly_points, outline=color_1, width=4)
        
        # Draw decorative lines (grid lines for synthwave)
        if "synthwave" in style_lower:
            for y in range(height//2, height, 40):
                draw.line([(0, y), (width, y)], fill=color_1, width=2)
            for x in range(0, width, 40):
                # perspective grid lines
                draw.line([(x, height//2), (x * 2 - width//2, height)], fill=color_1, width=2)
                
        # 3. Add text watermark overlay showing the prompt (to make it feel fully alive!)
        text_content = f"'{prompt[:30]}...'" if len(prompt) > 30 else f"'{prompt}'"
        watermark_text = f"Muse Spark Explorer | Seed: {seed} | Style: {style}"
        
        # Draw a beautiful container box
        draw.rectangle([10, height - 70, width - 10, height - 10], fill=(0,0,0,150), outline=color_2, width=1)
        
        # Draw watermark text
        # (Using fallback text since custom fonts may not be loaded in python sandbox)
        draw.text((20, height - 60), text_content, fill=(255,255,255))
        draw.text((20, height - 40), watermark_text, fill=(200,200,200))
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()
        
        result_payload = {
            "image_bytes": image_bytes,
            "format": "PNG",
            "prompt": prompt,
            "seed": seed,
            "style": style,
            "size": size,
            "quality": quality,
            "filename": f"gen_{seed}_{int(time.time())}.png"
        }
        
        return MuseSparkResponse(result_payload, latency=2.5)
