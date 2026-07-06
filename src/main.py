import asyncio
import logging

from app.container import Container
from infra.logger import setup_logging
from config import LOG_LEVEL

setup_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)


POLL_INTERVAL_SECONDS = 5000  # ms  # 5 минут


async def worker_loop(usecase):

    while True:
        try:
            logger.info("Starting update cycle")

            await usecase.execute()

            logger.info("Update cycle completed")

        except Exception as e:
            logger.exception("Update cycle failed: %s", e)

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def main():

    container = Container()

    try:
        await container.lifespan.start()

        usecase = container.update_usecase()

        await worker_loop(usecase)

    finally:
        await container.lifespan.stop()


if __name__ == "__main__":
    asyncio.run(main())
