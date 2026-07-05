from flask import Blueprint, render_template, redirect, url_for, request, session, flash, jsonify, current_app
from src.auth import login_required
from src.services.ai_service import ai_service
from src.security import limiter
from src.logger import logger
import time

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Index route redirects to login or dashboard based on authentication status."""
    if 'auth_token' in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
@limiter.limit("30 per minute")
def dashboard():
    """Renders the main system dashboard showing telemetry, requests statistics, and recent activities."""
    stats = ai_service.get_stats()
    return render_template('dashboard.html', stats=stats)


@main_bp.route('/api-status')
@login_required
def status():
    """Checks the status of the Muse Spark SDK and underlying connections."""
    start_time = time.time()
    api_key = current_app.config.get("MUSE_SPARK_API_KEY", "demo")
    base_url = current_app.config.get("MUSE_SPARK_BASE_URL", "http://localhost:8000")
    
    is_simulated = api_key == "demo"
    latency = 0.0
    online = True
    details = "Operational - Simulator Mode active."

    if not is_simulated:
        try:
            import httpx
            # Send a quick request to the base url to verify if it's reachable
            response = httpx.get(f"{base_url}/health" if "localhost" in base_url else base_url, timeout=3.0)
            latency = time.time() - start_time
            if response.status_code >= 500:
                online = False
                details = f"Unhealthy - Server returned status {response.status_code}"
            else:
                details = f"Active - Remote API endpoint connected successfully. Status: {response.status_code}"
        except Exception as e:
            online = False
            details = f"Unreachable - Connection failed: {str(e)}"
            logger.error(f"Status check failed for remote API {base_url}: {e}")

    status_data = {
        "online": online,
        "mode": "Simulator (Offline Demo)" if is_simulated else "Cloud-Ready (Live API)",
        "endpoint": base_url,
        "latency_ms": round(latency * 1000, 2) if not is_simulated else 0.0,
        "details": details,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # If AJAX, return json
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(status_data)

    return render_template('status.html', status_data=status_data)


@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Allows user to customize default model settings and reset request telemetry."""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'reset_telemetry':
            ai_service.reset_stats()
            flash("Telemetry statistics have been successfully reset.", "success")
            return redirect(url_for('main.settings'))
            
        # Update session settings defaults
        try:
            temp = float(request.form.get('default_temperature', 0.7))
            max_tok = int(request.form.get('default_max_tokens', 1000))
            sys_prompt = request.form.get('default_system_prompt', '').strip()
            
            if not (0.0 <= temp <= 2.0):
                flash("Temperature must be between 0.0 and 2.0", "danger")
                return redirect(url_for('main.settings'))
            if max_tok <= 0 or max_tok > 4000:
                flash("Max tokens must be between 1 and 4000", "danger")
                return redirect(url_for('main.settings'))
                
            session['chat_temperature'] = temp
            session['chat_max_tokens'] = max_tok
            session['chat_system_prompt'] = sys_prompt
            
            logger.info(f"User updated default chat session parameters: temp={temp}, max_tokens={max_tok}")
            flash("Default model parameters updated successfully.", "success")
        except ValueError:
            flash("Invalid input values. Please provide numbers.", "danger")
            
        return redirect(url_for('main.settings'))

    # Load from session or default configs
    current_settings = {
        "temperature": session.get('chat_temperature', 0.7),
        "max_tokens": session.get('chat_max_tokens', 1000),
        "system_prompt": session.get('chat_system_prompt', "You are Muse Spark, a helpful natively multimodal AI assistant created by Meta.")
    }
    return render_template('settings.html', settings=current_settings)


@main_bp.route('/about')
@login_required
def about():
    """Renders the About informational view."""
    return render_template('about.html')
