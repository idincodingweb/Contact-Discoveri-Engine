import logging
from rich.logging import RichHandler


def setup_logger(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )
    # Mute noisy libs
    for noisy in ("httpx", "httpcore", "asyncio", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
