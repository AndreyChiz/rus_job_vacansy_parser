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

        async def on_vacancy(vacancy):
            await sink.push(vacancy.model_dump_json())
            logger.info("Pushed vacancy: %s [%s]", vacancy.vacancy_id, vacancy.host)

        async def run_parse(body: dict):
            await status.set_running()

            try:
                hosts = body.get("hosts")
                query = body.get("query")

                vacancies = await usecase.execute(hosts=hosts, query=query, on_vacancy=on_vacancy)

                logger.info("Completed: %d vacancies total", len(vacancies))
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
