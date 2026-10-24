import logging
import sys
from rich.logging import RichHandler


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("jarvis")
    if not logger.handlers:
        logger.setLevel(level)
        handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=True,
            show_path=False
        )
        formatter = logging.Formatter("[bold cyan]JARVIS[/bold cyan] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = setup_logging()
