from typing import Any
from redis.asyncio import Redis

from core.base.base_cache import BaseCacheProvider, BaseCacheBackend
from core.base.base_lifespan import BaseLifecycle


# =========================
# BACKEND INTERFACES
# =========================

class CacheBackend:
    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: str, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> bool: ...
    async def sadd(self, key: str, value: str) -> None: ...
    async def sismember(self, key: str, value: str) -> bool: ...


# =========================
# MEMORY
# =========================

class MemoryCacheBackend(BaseCacheBackend):
    def __init__(self):
        self.kv: dict[str, Any] = {}
        self.sets: dict[str, set] = {}

    async def get(self, key: str) -> Any | None:
        return self.kv.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self.kv[key] = value

    async def delete(self, key: str) -> None:
        self.kv.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self.kv

    async def sadd(self, key: str, value: str) -> None:
        self.sets.setdefault(key, set()).add(value)

    async def sismember(self, key: str, value: str) -> bool:
        return value in self.sets.get(key, set())


# =========================
# REDIS
# =========================

class RedisCacheBackend(BaseCacheBackend, BaseLifecycle):
    def __init__(self, url: str):
        self.url = url
        self.redis: Redis | None = None

    async def start(self) -> None:
        self.redis = Redis.from_url(self.url, decode_responses=True)

    async def stop(self) -> None:
        if self.redis:
            await self.redis.aclose()
        self.redis = None

    def _client(self) -> Redis:
        if self.redis is None:
            raise RuntimeError("Redis not started")
        return self.redis

    async def get(self, key: str) -> Any | None:
        return await self._client().get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        await self._client().set(key, value, ex=ttl)

    async def delete(self, key: str) -> None:
        await self._client().delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self._client().exists(key))

    async def sadd(self, key: str, value: str) -> None:
        await self._client().sadd(key, value)

    async def sismember(self, key: str, value: str) -> bool:
        return bool(await self._client().sismember(key, value))


class CacheProvider(BaseCacheProvider, BaseLifecycle):
    def __init__(self, cache_type: str, url: str | None = None):
        self.cache_type = cache_type
        self.url = url
        self.backend: BaseCacheBackend | None = None

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

    def _b(self) -> BaseCacheBackend:
        if self.backend is None:
            raise RuntimeError("Cache not started")
        return self.backend

    def get_instance(self) -> "CacheProvider":
        return self

    async def get(self, key: str) -> Any | None:
        return await self._b().get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        await self._b().set(key, value, ttl)

    async def delete(self, key: str) -> None:
        await self._b().delete(key)

    async def exists(self, key: str) -> bool:
        return await self._b().exists(key)

    async def sadd(self, key: str, value: str) -> None:
        await self._b().sadd(key, value)

    async def sismember(self, key: str, value: str) -> bool:
        return await self._b().sismember(key, value)