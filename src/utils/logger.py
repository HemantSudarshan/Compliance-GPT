"""
logger.py - Centralized Logging Configuration

Provides structured logging with colored output and file rotation.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import os

# ANSI color codes for console output
COLORS = {
    'DEBUG': '\033[36m',      # Cyan
    'INFO': '\033[32m',       # Green
    'WARNING': '\033[33m',    # Yellow
    'ERROR': '\033[31m',      # Red
    'CRITICAL': '\033[35m',   # Magenta
    'RESET': '\033[0m',       # Reset
}


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    def __init__(self, fmt: str = None, datefmt: str = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors:
            color = COLORS.get(record.levelname, COLORS['RESET'])
            reset = COLORS['RESET']
            record.levelname = f"{color}{record.levelname}{reset}"
            record.name = f"\033[34m{record.name}{reset}"
        return super().format(record)


class ComplianceGPTLogger:
    """
    Centralized logging configuration for ComplianceGPT.
    
    Features:
    - Colored console output
    - File logging with rotation
    - Structured format for parsing
    - Different log levels for different outputs
    """
    
    _loggers: dict = {}
    _initialized: bool = False
    _log_dir: Optional[Path] = None
    
    @classmethod
    def setup(
        cls,
        log_level: str = None,
        log_dir: Optional[str] = None,
        enable_file_logging: bool = True
    ) -> None:
        """
        Initialize the logging system.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_dir: Directory for log files
            enable_file_logging: Whether to write logs to files
        """
        if cls._initialized:
            return
        
        # Get log level from environment or default
        level = log_level or os.getenv("LOG_LEVEL", "INFO")
        level = getattr(logging, level.upper(), logging.INFO)
        
        # Set up log directory
        if enable_file_logging:
            cls._log_dir = Path(log_dir) if log_dir else Path(__file__).parent.parent.parent / "logs"
            cls._log_dir.mkdir(exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Remove existing handlers
        root_logger.handlers.clear()
        
        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_fmt = "%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s"
        console_handler.setFormatter(ColoredFormatter(console_fmt, datefmt="%H:%M:%S"))
        root_logger.addHandler(console_handler)
        
        # File handler (if enabled)
        if enable_file_logging and cls._log_dir:
            log_file = cls._log_dir / f"compliancegpt_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)  # Capture all levels in file
            file_fmt = "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
            file_handler.setFormatter(logging.Formatter(file_fmt))
            root_logger.addHandler(file_handler)
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get or create a logger with the given name."""
        if name not in cls._loggers:
            if not cls._initialized:
                cls.setup()
            cls._loggers[name] = logging.getLogger(name)
        return cls._loggers[name]


def setup_logger(name: str, level: str = None) -> logging.Logger:
    """
    Convenience function to set up and get a logger.
    
    Args:
        name: Logger name (usually __name__)
        level: Optional log level override
        
    Returns:
        Configured logger instance
    """
    ComplianceGPTLogger.setup()
    logger = ComplianceGPTLogger.get_logger(name)
    
    if level:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    return logger


# Quick access functions
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return setup_logger(name)


def debug(msg: str, *args, **kwargs):
    """Log a debug message."""
    logging.debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """Log an info message."""
    logging.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """Log a warning message."""
    logging.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """Log an error message."""
    logging.error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """Log a critical message."""
    logging.critical(msg, *args, **kwargs)


# Initialize on module import
if __name__ != "__main__":
    ComplianceGPTLogger.setup(enable_file_logging=False)
