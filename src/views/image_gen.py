import os
from flask import Blueprint, render_template, request, jsonify, current_app, send_from_directory
from src.auth import login_required
from src.services.ai_service import ai_service
from src.security import limiter
from src.errors import InvalidInputError, MuseSparkError
from src.logger import logger

image_gen_bp = Blueprint('image_gen', __name__)

@image_gen_bp.route('/image-gen')
@login_required
def image_gen():
    """Renders the image generation page."""
    return render_template('image_gen.html')


@image_gen_bp.route('/image-gen/generate', methods=['POST'])
@login_required
@limiter.limit("5 per minute")  # Moderate generation rate limit
def generate():
    """
    Handles request for image generation, parses inputs, triggers the SDK,
    saves the output image bytes to a static path, and returns metadata.
    """
    data = request.get_json() or {}
    
    prompt = data.get('prompt', '').strip()
    negative_prompt = data.get('negative_prompt', '').strip() or None
    size = data.get('size', '512x512')
    quality = data.get('quality', 'standard')
    style = data.get('style', 'photorealistic')
    seed = data.get('seed')

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    # Parse and validate seed if provided
    parsed_seed = None
    if seed:
        try:
            parsed_seed = int(seed)
            if parsed_seed < 0:
                return jsonify({"error": "Seed must be a positive integer"}), 400
        except ValueError:
            return jsonify({"error": "Seed must be a numeric integer"}), 400

    try:
        # Create output directory for generated assets
        generated_dir = current_app.config.get("GENERATED_FOLDER")
        if not os.path.exists(generated_dir):
            os.makedirs(generated_dir)

        # Call AI Service
        result_payload, latency = ai_service.generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            size=size,
            quality=quality,
            style=style,
            seed=parsed_seed
        )

        filename = result_payload["filename"]
        image_bytes = result_payload["image_bytes"]
        
        # Save image file to static folder
        filepath = os.path.join(generated_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)

        logger.info(f"Generated image saved to: {filepath}")

        # Return json package for UI update
        return jsonify({
            "success": True,
            "url": f"/static/generated/{filename}",
            "filename": filename,
            "prompt": prompt,
            "style": style,
            "size": size,
            "quality": quality,
            "seed": result_payload["seed"],
            "latency_sec": round(latency, 2)
        })

    except MuseSparkError as e:
        logger.error(f"Image generation SDK error: {e}")
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        logger.error(f"Unexpected image generation route failure: {e}")
        return jsonify({"error": f"Failed to generate image: {str(e)}"}), 500
