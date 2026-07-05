import os
import json
import time
import threading
from src.config import Config
from src.sdk.client import MuseSpark
from src.logger import logger
from src.errors import MuseSparkError

# Global thread lock for telemetry updates
stats_lock = threading.Lock()
STATS_FILE = os.path.join("data", "stats.json")

def init_stats():
    """Initializes the data folder and stats.json file if they do not exist."""
    with stats_lock:
        data_dir = os.path.dirname(STATS_FILE)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        if not os.path.exists(STATS_FILE):
            default_stats = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_latency": 0.0,
                "average_latency": 0.0,
                "recent_activities": []
            }
            try:
                with open(STATS_FILE, "w", encoding="utf-8") as f:
                    json.dump(default_stats, f, indent=4)
            except Exception as e:
                logger.error(f"Failed to initialize stats file: {e}")

class AIService:
    """
    Main Service for interacting with Muse Spark SDK.
    Handles telemetry tracking, error catching, and structured logging.
    """
    def __init__(self, app=None):
        self.client = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initializes the service with application configuration."""
        api_key = app.config.get("MUSE_SPARK_API_KEY", "demo")
        base_url = app.config.get("MUSE_SPARK_BASE_URL", "http://localhost:8000")
        self.client = MuseSpark(api_key=api_key, base_url=base_url)
        init_stats()

    def get_stats(self):
        """Returns the current telemetry stats dictionary."""
        init_stats()
        with stats_lock:
            try:
                with open(STATS_FILE, "r", encoding="utf-8") as f:
                    stats = json.load(f)
                    # Recalculate average latency just in case
                    total = stats.get("total_requests", 0)
                    if total > 0:
                        stats["average_latency"] = round(stats["total_latency"] / total, 3)
                    else:
                        stats["average_latency"] = 0.0
                    return stats
            except Exception as e:
                logger.error(f"Error reading stats file: {e}")
                return {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "total_latency": 0.0,
                    "average_latency": 0.0,
                    "recent_activities": []
                }

    def reset_stats(self):
        """Resets the telemetry stats."""
        init_stats()
        with stats_lock:
            default_stats = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_latency": 0.0,
                "average_latency": 0.0,
                "recent_activities": []
            }
            try:
                with open(STATS_FILE, "w", encoding="utf-8") as f:
                    json.dump(default_stats, f, indent=4)
                logger.info("Telemetry statistics have been reset.")
            except Exception as e:
                logger.error(f"Error resetting stats file: {e}")

    def _record_activity(self, action_name, latency, success=True):
        """Appends telemetry information in a thread-safe manner."""
        init_stats()
        with stats_lock:
            try:
                with open(STATS_FILE, "r+", encoding="utf-8") as f:
                    stats = json.load(f)
                    
                    stats["total_requests"] += 1
                    if success:
                        stats["successful_requests"] += 1
                    else:
                        stats["failed_requests"] += 1
                    
                    stats["total_latency"] += latency
                    
                    # Log activity entry
                    activity_entry = {
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "action": action_name,
                        "latency_sec": round(latency, 3),
                        "status": "Success" if success else "Failed"
                    }
                    
                    # Keep only last 25 recent activities
                    recent = stats.get("recent_activities", [])
                    recent.insert(0, activity_entry)
                    stats["recent_activities"] = recent[:25]
                    
                    # Write back to file
                    f.seek(0)
                    json.dump(stats, f, indent=4)
                    f.truncate()
            except Exception as e:
                logger.error(f"Error recording telemetry activity: {e}")

    def stream_chat(self, messages, temperature=0.7, max_tokens=1000, system_prompt=None):
        """
        Wraps SDK streaming chat completions and yields tokens.
        Logs latency dynamically.
        """
        start_time = time.time()
        success = False
        action_name = "Streaming Chat Completion"
        
        try:
            logger.info(f"Initiating stream chat with temp={temperature}, max_tokens={max_tokens}")
            chunk_generator = self.client.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
                stream=True
            )
            
            # We yield tokens and measure duration on completion
            total_tokens = 0
            for chunk in chunk_generator:
                if chunk.content:
                    total_tokens += 1
                    yield chunk.content
                if chunk.is_final:
                    success = True
                    
            latency = time.time() - start_time
            self._record_activity(action_name, latency, success)
            logger.info(f"Stream chat completion finished in {latency:.3f}s (approx {total_tokens} chunks).")
            
        except Exception as e:
            latency = time.time() - start_time
            self._record_activity(action_name, latency, success=False)
            logger.error(f"Exception during stream chat service: {e}")
            raise e

    def vision_analyze(self, image_bytes, filename, content_type):
        """
        Interfaces with image analysis SDK method.
        Records response metrics.
        """
        start_time = time.time()
        action_name = f"Vision Analysis ({filename})"
        try:
            logger.info(f"Sending image {filename} ({len(image_bytes)} bytes) for vision analysis.")
            response = self.client.vision_analyze(image_bytes, filename, content_type)
            latency = time.time() - start_time
            self._record_activity(action_name, latency, success=True)
            logger.info(f"Vision analysis completed in {latency:.3f}s.")
            return response.content, latency
        except Exception as e:
            latency = time.time() - start_time
            self._record_activity(action_name, latency, success=False)
            logger.error(f"Vision service failure: {e}")
            raise e

    def generate_image(self, prompt, negative_prompt=None, size="512x512", quality="standard", style="photorealistic", seed=None):
        """
        Interfaces with image generation SDK method.
        Records telemetry metrics.
        """
        start_time = time.time()
        action_name = f"Image Generation ({style})"
        try:
            logger.info(f"Requesting image generation for prompt: '{prompt}' style={style} seed={seed}")
            response = self.client.generate_image(
                prompt=prompt,
                negative_prompt=negative_prompt,
                size=size,
                quality=quality,
                style=style,
                seed=seed
            )
            latency = time.time() - start_time
            self._record_activity(action_name, latency, success=True)
            logger.info(f"Image generation completed in {latency:.3f}s.")
            return response.content, latency
        except Exception as e:
            latency = time.time() - start_time
            self._record_activity(action_name, latency, success=False)
            logger.error(f"Image generation service failure: {e}")
            raise e

# Create global AIService singleton
ai_service = AIService()
