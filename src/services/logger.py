import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Constants
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.INFO
LOG_DIR = 'logs'
MAX_BYTES = 5 * 1024 * 1024  # 5MB
BACKUP_COUNT = 5

def setup_logger():
    """
    Sets up the application's logging configuration
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # Generate log filename with date
    log_file = os.path.join(
        LOG_DIR,
        f'app_{datetime.now().strftime("%Y%m%d")}.log'
    )

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT)

    # Setup file handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

def get_logger(name):
    """
    Gets a logger instance for the specified name
    """
    return logging.getLogger(name)

# Setup logging when module is imported
setup_logger()
