import asyncio
import logging

from redis.asyncio import Redis

from app.container import Container
from transport.amqp.mq_provider import MQProvider
from transport.amqp.handler import VacancyParseHandler
from transport.redis.status_flag import RedisStatusFlag
from transport.redis.vacancy_sink import RedisVacancySink
from infra.logger import setup_logging
from config import LOG_LEVEL, RABBITMQ_URL, CACHE_URL

setup_logging(LOG_LEVEL)
logger = logging.getLogger(__name__)

LOCK_TTL = 600


async def main():

    container = Container()
    mq = MQProvider(url=RABBITMQ_URL)
    redis = Redis.from_url(CACHE_URL, decode_responses=True)

    try:
        await container.lifespan.start()
        await mq.start()

        usecase = container.parse_usecase()
        sink = RedisVacancySink(redis)
        status = RedisStatusFlag(redis, ttl=LOCK_TTL)

        async def run_parse():
            await status.set_running()

            try:
                vacancies = await usecase.execute()

                for vacancy in vacancies:
                    await sink.push(vacancy.model_dump_json())

                logger.info("Pushed %d vacancies to queue", len(vacancies))
            finally:
                await status.clear_running()

        handler = VacancyParseHandler(
            mq_channel=mq.get_channel(),
            on_parse=run_parse,
        )

        await handler.start_consuming()

        await asyncio.Future()

    finally:
        await mq.stop()
        await redis.aclose()
        await container.lifespan.stop()


if __name__ == "__main__":
    asyncio.run(main())
