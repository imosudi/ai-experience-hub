import json
from flask import Blueprint, render_template, request, Response, stream_with_context, session, jsonify
from src.auth import login_required
from src.services.ai_service import ai_service
from src.security import limiter
from src.errors import InvalidInputError
from src.logger import logger

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat')
@login_required
def chat():
    """Renders the multi-turn streaming chat page."""
    # Pre-populate settings from session or defaults
    settings = {
        "temperature": session.get('chat_temperature', 0.7),
        "max_tokens": session.get('chat_max_tokens', 1000),
        "system_prompt": session.get('chat_system_prompt', "You are Muse Spark, a helpful natively multimodal AI assistant created by Meta.")
    }
    return render_template('chat.html', settings=settings)


@chat_bp.route('/chat/stream', methods=['POST'])
@login_required
@limiter.limit("10 per minute")  # Moderate rate-limit for inference endpoints
def stream():
    """
    Handles streaming chat completion requests.
    Reads history, parameters, and system prompts, then streams token outputs
    using Server-Sent Events (SSE).
    """
    data = request.get_json() or {}
    
    messages = data.get('messages', [])
    temperature = data.get('temperature')
    max_tokens = data.get('max_tokens')
    system_prompt = data.get('system_prompt')

    # Fallback to session values or configs if not provided in request
    if temperature is None:
        temperature = session.get('chat_temperature', 0.7)
    if max_tokens is None:
        max_tokens = session.get('chat_max_tokens', 1000)
    if system_prompt is None:
        system_prompt = session.get('chat_system_prompt', "You are Muse Spark, a helpful natively multimodal AI assistant created by Meta.")

    # Cast parameters and validate
    try:
        temperature = float(temperature)
        max_tokens = int(max_tokens)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid temperature or max_tokens type."}), 400

    if not messages:
        return jsonify({"error": "Messages history cannot be empty."}), 400

    logger.info(f"Chat stream endpoint called: temperature={temperature}, max_tokens={max_tokens}")

    def generate_events():
        try:
            # Call streaming AI service
            for token in ai_service.stream_chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt
            ):
                # Send token in JSON-SSE wrapper
                yield f"data: {json.dumps({'token': token})}\n\n"
            
            # Send completion signal
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            logger.error(f"Error during streaming execution: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    # Return standard event stream headers
    response = Response(stream_with_context(generate_events()), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'  # Disable Nginx buffering if deployed
    return response
