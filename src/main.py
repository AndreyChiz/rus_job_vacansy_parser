import asyncio
import logging

from app.container import Container
from transport.amqp.mq_provider import MQProvider
from transport.amqp.handler import VacancyParseHandler
from infra.logger import setup_logging
from config import LOG_LEVEL, RABBITMQ_URL

setup_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)


async def main():

    container = Container()
    mq = MQProvider(url=RABBITMQ_URL)

    try:
        await container.lifespan.start()
        await mq.start()

        handler = VacancyParseHandler(
            mq_channel=mq.get_channel(),
            parse_usecase=container.parse_usecase(),
        )

        await handler.start_consuming()

        await asyncio.Future()

    finally:
        await mq.stop()
        await container.lifespan.stop()


if __name__ == "__main__":
    asyncio.run(main())
