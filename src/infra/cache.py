from abc import ABC, abstractmethod
from redis.asyncio import Redis

from core.base.base_lifespan import BaseLifecycle


class CacheBackend(ABC):

    @abstractmethod
    async def sadd(self, key: str, value: str) -> None:
        ...

    @abstractmethod
    async def sismember(self, key: str, value: str) -> bool:
        ...

    @abstractmethod
    async def smembers(self, key: str) -> set[str]:
        ...


class MemoryCacheBackend(CacheBackend):
    def __init__(self) -> None:
        self.sets: dict[str, set[str]] = {}

    async def sadd(self, key: str, value: str) -> None:
        self.sets.setdefault(key, set()).add(value)

    async def sismember(self, key: str, value: str) -> bool:
        return value in self.sets.get(key, set())

    async def smembers(self, key: str) -> set[str]:
        return self.sets.get(key, set())


class RedisCacheBackend(CacheBackend, BaseLifecycle):
    def __init__(self, url: str):
        self.url = url
        self.redis: Redis | None = None

    async def start(self) -> None:
        self.redis = Redis.from_url(self.url, decode_responses=True)

    async def stop(self) -> None:
        if self.redis:
            await self.redis.aclose()
        self.redis = None

    def get_client(self) -> Redis:
        if self.redis is None:
            raise RuntimeError("Redis not started")
        return self.redis

    async def sadd(self, key: str, value: str) -> None:
        await self.get_client().sadd(key, value)

    async def sismember(self, key: str, value: str) -> bool:
        return bool(await self.get_client().sismember(key, value))

    async def smembers(self, key: str) -> set[str]:
        result: set[str] = await self.get_client().smembers(key)  # type: ignore[assignment]
        return result


class CacheProvider(BaseLifecycle):
    def __init__(self, cache_type: str, url: str | None = None):
        self.cache_type = cache_type
        self.url = url
        self.backend: CacheBackend | None = None

    async def start(self) -> None:
        if self.cache_type == "memory":
            self.backend = MemoryCacheBackend()
            return

        if self.cache_type == "redis":
            if not self.url:
                raise ValueError("cache_url is required for redis")

            backend = RedisCacheBackend(self.url)
            await backend.start()
            self.backend = backend
            return

        raise ValueError(f"Unsupported cache_type: {self.cache_type}")

    async def stop(self) -> None:
        if isinstance(self.backend, RedisCacheBackend):
            await self.backend.stop()

        self.backend = None

    def get_backend(self) -> CacheBackend:
        if self.backend is None:
            raise RuntimeError("Cache not started")
        return self.backend

    def get_instance(self) -> "CacheProvider":
        return self

    async def sadd(self, key: str, value: str) -> None:
        await self.get_backend().sadd(key, value)

    async def sismember(self, key: str, value: str) -> bool:
        return await self.get_backend().sismember(key, value)

    async def smembers(self, key: str) -> set[str]:
        return await self.get_backend().smembers(key)
