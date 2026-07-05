from flask import Blueprint, render_template, request, jsonify
from src.auth import login_required
from src.services.agent_service import agent_service
from src.security import limiter
from src.errors import MuseSparkError, InvalidInputError, SDKConnectionError
from src.logger import logger

agent_bp = Blueprint('agent', __name__)

@agent_bp.route('/agent')
@login_required
def agent_view():
    """Renders the AI Agent (Webpage Summarizer) interface."""
    return render_template('agent.html')


@agent_bp.route('/agent/run', methods=['POST'])
@login_required
@limiter.limit("10 per minute")  # Rate limit agent scrape cycles
def run_agent():
    """
    Triggers the webpage agent pipeline: resolves and validates the URL,
    downloads the target, parses/cleans HTML content, and queries Muse Spark.
    """
    data = request.get_json() or {}
    url = data.get('url', '').strip()

    if not url:
        return jsonify({"error": "Webpage URL is required"}), 400

    logger.info(f"AI Agent triggered for URL: {url}")

    try:
        # Run agent pipeline
        result = agent_service.summarize_webpage(url)
        return jsonify(result)

    except InvalidInputError as e:
        logger.warning(f"Agent URL/Content validation issue: {e}")
        return jsonify({"error": e.message}), 400
    except SDKConnectionError as e:
        logger.error(f"Agent remote fetch failure: {e}")
        return jsonify({"error": f"Failed to fetch or reach the target webpage: {e.message}"}), 502
    except MuseSparkError as e:
        logger.error(f"Agent SDK summarization failure: {e}")
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        logger.error(f"Unexpected agent pipeline failure: {e}")
        return jsonify({"error": f"An unexpected error occurred during agent execution: {str(e)}"}), 500
