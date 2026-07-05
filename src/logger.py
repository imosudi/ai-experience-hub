import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logger(name="muse_explorer", log_level=logging.INFO):
    """
    Sets up a structured logger that writes to both the console and a rotating file.
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Avoid duplicate handlers if already initialized
    if logger.handlers:
        return logger

    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_format = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s (line %(lineno)d) [%(process)d]: %(message)s"
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)

    # Rotating File Handler (10MB, keep 5 backups)
    log_file = os.path.join(log_dir, "muse_explorer.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(log_format)
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger

# Create default logger instance
logger = setup_logger()
