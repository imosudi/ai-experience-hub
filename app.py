import os
from src.app import create_app
from src.logger import logger

# Retrieve the environment mode, defaulting to development
env = os.getenv("APP_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    debug_mode = app.config.get("DEBUG", False)
    logger.info(f"Running development server on port 5000 (debug={debug_mode})")
    
    # Run server on port 5000
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
