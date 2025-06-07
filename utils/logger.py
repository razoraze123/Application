import logging
import os


def setup_logger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger:
    """Create and configure a logger that writes to a file and the console."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    formatter_file = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter_file)

    formatter_console = logging.Formatter('%(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter_console)

    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

