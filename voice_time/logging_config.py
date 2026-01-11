"""
Logging configuration for TimeBrief.

Provides:
- Console logging (INFO level for production, DEBUG for development)
- File logging with rotation
- Separate dev.log for development troubleshooting
- Startup error capture
"""
import os
import sys
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime


def get_log_dir() -> Path:
    """Get the log directory, creating it if necessary."""
    # Use user's data directory
    if sys.platform == 'win32':
        base = Path(os.environ.get('USERPROFILE', '.'))
    else:
        base = Path.home()

    log_dir = base / '.voice_time' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logging(
    level: str = 'INFO',
    dev_mode: bool = False,
    log_to_file: bool = True
) -> logging.Logger:
    """
    Configure logging for TimeBrief.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        dev_mode: If True, enables verbose logging to dev.log
        log_to_file: If True, writes logs to files

    Returns:
        The root logger configured for the application
    """
    log_dir = get_log_dir()

    # Determine log level
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )

    # Get root logger for voice_time
    root_logger = logging.getLogger('voice_time')
    root_logger.setLevel(logging.DEBUG if dev_mode else log_level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    if log_to_file:
        # Main application log (rotating, 5MB max, keep 3 backups)
        app_log_path = log_dir / 'timebrief.log'
        file_handler = logging.handlers.RotatingFileHandler(
            app_log_path,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

        # Error log (errors only)
        error_log_path = log_dir / 'errors.log'
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_path,
            maxBytes=2 * 1024 * 1024,  # 2MB
            backupCount=2,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)

        # Dev log (for development - captures everything)
        if dev_mode:
            dev_log_path = log_dir / 'dev.log'
            dev_handler = logging.handlers.RotatingFileHandler(
                dev_log_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=1,
                encoding='utf-8'
            )
            dev_handler.setLevel(logging.DEBUG)
            dev_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(dev_handler)

    # Also configure Flask and Werkzeug loggers
    for logger_name in ['werkzeug', 'flask', 'flask.app']:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        logger.handlers.clear()
        logger.addHandler(console_handler)
        if log_to_file:
            logger.addHandler(file_handler)

    # Reduce noise from some libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)

    return root_logger


def log_startup_info(logger: logging.Logger) -> None:
    """Log startup information for debugging."""
    logger.info("=" * 60)
    logger.info("TimeBrief Starting")
    logger.info("=" * 60)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Log directory: {get_log_dir()}")

    # Log environment
    logger.debug(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'not set')}")
    logger.debug(f"PATH: {os.environ.get('PATH', 'not set')[:200]}...")


def log_exception(logger: logging.Logger, exc: Exception, context: str = "") -> None:
    """Log an exception with full traceback."""
    import traceback

    logger.error("=" * 60)
    logger.error(f"EXCEPTION: {context}" if context else "EXCEPTION OCCURRED")
    logger.error("=" * 60)
    logger.error(f"Type: {type(exc).__name__}")
    logger.error(f"Message: {str(exc)}")
    logger.error("Traceback:")
    for line in traceback.format_exc().split('\n'):
        logger.error(line)
    logger.error("=" * 60)


def write_crash_log(exc: Exception, context: str = "") -> Path:
    """
    Write a crash log file for immediate debugging.
    Returns the path to the crash log.
    """
    import traceback

    log_dir = get_log_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    crash_file = log_dir / f'crash_{timestamp}.log'

    with open(crash_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write(f"TimeBrief Crash Report\n")
        f.write(f"Time: {datetime.now().isoformat()}\n")
        f.write("=" * 60 + "\n\n")

        if context:
            f.write(f"Context: {context}\n\n")

        f.write(f"Exception Type: {type(exc).__name__}\n")
        f.write(f"Exception Message: {str(exc)}\n\n")

        f.write("Full Traceback:\n")
        f.write(traceback.format_exc())

        f.write("\n\nSystem Information:\n")
        f.write(f"Python: {sys.version}\n")
        f.write(f"Platform: {sys.platform}\n")
        f.write(f"CWD: {os.getcwd()}\n")

    return crash_file
