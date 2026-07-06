import aio_pika
from core.base.base_lifespan import BaseLifecycle


class MQProvider(BaseLifecycle):
    def __init__(self, url: str):
        self.url = url
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.Channel | None = None

    async def start(self) -> None:
        self.connection = await aio_pika.connect_robust(self.url)
        self.channel = await self.connection.channel()

    async def stop(self) -> None:
        if self.connection:
            await self.connection.close()
        self.connection = None
        self.channel = None

    def get_channel(self) -> aio_pika.Channel:
        if self.channel is None:
            raise RuntimeError("MQ not started")
        return self.channel
