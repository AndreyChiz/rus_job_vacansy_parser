from redis.asyncio import Redis


class RedisStatusFlag:
    def __init__(self, redis: Redis, key: str = "vacancy:parser:running", ttl: int = 600):
        self.redis = redis
        self.key = key
        self.ttl = ttl

    async def set_running(self) -> None:
        await self.redis.set(self.key, "1", ex=self.ttl)

    async def clear_running(self) -> None:
        await self.redis.delete(self.key)
