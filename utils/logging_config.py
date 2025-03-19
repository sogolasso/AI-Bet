"""
Logging configuration for the AI Football Betting Advisor.
Sets up logging with emoji support and proper encoding.
"""

import os
import sys
import logging
from pathlib import Path
from utils.emoji_utils import sanitize_for_console

class EmojiSafeFormatter(logging.Formatter):
    """
    Custom formatter that sanitizes emojis for console output.
    """
    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)
        
    def format(self, record):
        # Format the message as usual
        formatted_message = super().format(record)
        
        # Sanitize emojis for console output
        return sanitize_for_console(formatted_message)

def setup_logging(logger_name, log_file=None, console_level=logging.INFO, file_level=logging.DEBUG):
    """
    Set up logging configuration for the application.
    
    Args:
        logger_name (str): Name of the logger
        log_file (str, optional): Path to log file. If None, only console logging is enabled.
        console_level (int, optional): Logging level for console output. Defaults to logging.INFO.
        file_level (int, optional): Logging level for file output. Defaults to logging.DEBUG.
    
    Returns:
        logging.Logger: Configured logger
    """
    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)  # Set to lowest level to capture everything
    
    # Remove existing handlers if any
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler with emoji-safe formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    console_formatter = EmojiSafeFormatter(console_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log_file is specified
    if log_file:
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Set up file handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(file_level)
        file_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        file_formatter = logging.Formatter(file_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger 