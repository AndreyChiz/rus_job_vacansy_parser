import logging
import sys


# цель: ANSI цвета
class Colors:
    RESET = "\033[0m"
    GRAY = "\033[90m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"


# цель: цветной formatter с line number
class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # цель: timestamp
        asctime = self.formatTime(record, "%Y-%m-%d %H:%M:%S,%f")[:-3]

        # цель: уровень логирования
        level_color = {
            "DEBUG": Colors.CYAN,
            "INFO": Colors.GREEN,
            "WARNING": Colors.YELLOW,
            "ERROR": Colors.RED,
            "CRITICAL": Colors.RED,
        }.get(record.levelname, Colors.RESET)

        # цель: module + line number (parsers.hh:14)
        location = f"{record.name}:{record.lineno}"

        return (
            f"{Colors.GRAY}{asctime}{Colors.RESET} | "
            f"{level_color}{record.levelname:<7}{Colors.RESET} | "
            f"{Colors.CYAN}{location}{Colors.RESET} | "
            f"{record.getMessage()}"
        )


# цель: настройка logging
def setup_logging(log_level: str| None) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorFormatter())

    logging.basicConfig(
        level=log_level,
        handlers=[handler],
        format="%(message)s",  # важно: отключаем стандартный формат
    )

    # цель: убрать шум asyncio
    logging.getLogger("asyncio").setLevel(logging.WARNING)