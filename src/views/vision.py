import io
from flask import Blueprint, render_template, request, jsonify, current_app
from src.auth import login_required
from src.services.ai_service import ai_service
from src.security import limiter
from src.errors import InvalidInputError, MuseSparkError
from src.logger import logger
from PIL import Image

vision_bp = Blueprint('vision', __name__)

def allowed_file(filename):
    """Checks if file extension is allowed."""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@vision_bp.route('/vision')
@login_required
def vision():
    """Renders the computer vision upload and analysis page."""
    return render_template('vision.html')


@vision_bp.route('/vision/upload', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def upload_image():
    """
    Handles image upload, performs validation on file size and extension,
    extracts metadata using Pillow, and runs the vision analysis.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded in the request"}), 400

    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file name"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file format. Only JPG, PNG, and WEBP are supported."}), 400

    # Read image into memory to avoid saving to disk and validate structure
    try:
        image_bytes = file.read()
        file_size = len(image_bytes)
        
        # Enforce size limits manually in case server config didn't catch it
        max_size = current_app.config.get("MAX_UPLOAD_SIZE", 5242880)
        if file_size > max_size:
            logger.warning(f"File upload size ({file_size} bytes) exceeds limit ({max_size} bytes).")
            return jsonify({"error": f"File size exceeds the maximum limit of {max_size / (1024*1024):.1f}MB."}), 400

        # Validate image format and resolution using Pillow
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()  # Verify image structure is sound
            
            # Re-open after verify() because verify() closes the file pointer/resource
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
            img_format = img.format
        except Exception as img_err:
            logger.error(f"Image verification failed: {img_err}")
            return jsonify({"error": "Invalid or corrupted image file structure."}), 400

        # Perform Vision Analysis
        content_type = file.content_type or f"image/{img_format.lower()}"
        logger.info(f"Uploading image: {file.filename} (Size: {file_size} bytes, Res: {width}x{height})")
        
        analysis_result, latency = ai_service.vision_analyze(
            image_bytes=image_bytes,
            filename=file.filename,
            content_type=content_type
        )
        
        # Add visual metadata details for the frontend rendering
        analysis_result["metadata"] = {
            "filename": file.filename,
            "size_bytes": file_size,
            "size_formatted": f"{file_size / 1024:.1f} KB",
            "width": width,
            "height": height,
            "format": img_format
        }
        analysis_result["latency_sec"] = latency

        return jsonify(analysis_result)

    except MuseSparkError as e:
        logger.error(f"Muse Spark SDK vision analysis error: {e}")
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        logger.error(f"Unexpected vision upload failure: {e}")
        return jsonify({"error": f"Failed to complete vision analysis: {str(e)}"}), 500
