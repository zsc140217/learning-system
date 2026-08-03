"""
Logging configuration for Learning System

Fixes Windows terminal encoding issues:
- Forces UTF-8 encoding for console output
- Handles Windows CMD GBK encoding mismatch
- Provides structured logging with Loguru
"""
import sys
from loguru import logger


def setup_logging(level: str = "INFO") -> None:
    """
    Configure Loguru logger with UTF-8 encoding for Windows compatibility

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Remove default handler
    logger.remove()

    # Reconfigure stderr to use UTF-8 encoding
    # This fixes Windows GBK encoding mismatch
    import io
    if hasattr(sys.stderr, 'reconfigure'):
        # Python 3.7+ method
        sys.stderr.reconfigure(encoding='utf-8')
    else:
        # Fallback: wrap with TextIOWrapper
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer,
            encoding='utf-8',
            errors='replace',
            line_buffering=True
        )

    # Add console handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | {message}",
        level=level,
        colorize=True,
        enqueue=True
    )

    logger.info(f"Logging configured: level={level}, encoding=UTF-8")


def setup_file_logging(log_file: str, level: str = "DEBUG") -> None:
    """
    Add file logging handler

    Args:
        log_file: Path to log file
        level: Log level for file output
    """
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        level=level,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8"  # File handler supports encoding parameter
    )

    logger.info(f"File logging enabled: {log_file}")


# Configure on module import
setup_logging()
