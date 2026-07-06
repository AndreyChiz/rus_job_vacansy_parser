import aio_pika
from logging import getLogger

logger = getLogger(__name__)


class VacancyParseHandler:
    def __init__(self, mq_channel, parse_usecase):
        self.channel = mq_channel
        self.parse_usecase = parse_usecase

    async def start_consuming(self):
        exchange = await self.channel.declare_exchange(
            "vacancy.exchange", aio_pika.ExchangeType.DIRECT
        )
        queue = await self.channel.declare_queue("vacancy.parse.request", durable=True)
        await queue.bind(exchange, routing_key="vacancy.parse")
        logger.info("Consuming on vacancy.parse.request")
        await queue.consume(self._on_message)

    async def _on_message(self, message: aio_pika.IncomingMessage):
        async with message.process():
            logger.info("Received parse command: %s", message.body)
            try:
                await self.parse_usecase.execute()
            except Exception:
                logger.exception("Parse failed")
