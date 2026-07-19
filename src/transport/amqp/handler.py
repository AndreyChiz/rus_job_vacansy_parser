import json
import aio_pika
from typing import Callable, Awaitable
from logging import getLogger

logger = getLogger(__name__)


class VacancyParseHandler:
    def __init__(self, mq_channel, on_parse: Callable[[dict], Awaitable[None]]):
        self.channel = mq_channel
        self.on_parse = on_parse

    async def start_consuming(self):
        exchange = await self.channel.declare_exchange(
            "vacancy.exchange",
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )
        queue = await self.channel.declare_queue("vacancy.parser.request", durable=True)
        await queue.bind(exchange, routing_key="vacancy.parser")
        logger.info("Consuming on vacancy.parser.request")
        await queue.consume(self._on_message)

    async def _on_message(self, message: aio_pika.IncomingMessage):
        async with message.process():
            try:
                body = json.loads(message.body)
                logger.info("Received parse command: %s", body)
                await self.on_parse(body)
            except Exception:
                logger.exception("Parse failed")
