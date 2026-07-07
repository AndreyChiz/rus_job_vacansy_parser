import os
from dotenv import load_dotenv

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"
)

CACHE_TYPE = os.getenv("CACHE_TYPE", "redis")
CACHE_URL = os.getenv("CACHE_URL", "redis://localhost:6379/0")

PARALLEL_WORKERS = int(os.getenv("PARALLEL_WORKERS", "4"))
CARDS_PARSE_LIMIT = int(os.getenv("CARDS_PARSE_LIMIT", "10"))

BROWSER_TYPE = os.getenv("BROWSER_TYPE", "chromium")
