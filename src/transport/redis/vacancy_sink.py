from redis.asyncio import Redis


class RedisVacancySink:
    def __init__(self, redis: Redis, queue_key: str = "vacancy:queue"):
        self.redis = redis
        self.queue_key = queue_key

    async def push(self, vacancy_json: str) -> None:
        await self.redis.rpush(self.queue_key, vacancy_json)
