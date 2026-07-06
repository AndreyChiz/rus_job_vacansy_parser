from abc import ABC, abstractmethod
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


Dialect = Literal["sqlite", "postgres"]


class BaseDatabaseProvider(ABC):

    @property
    @abstractmethod
    def dialect(self) -> Dialect:
        ...

    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...

    @abstractmethod
    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        ...

class BaseDatabaseBackend:
    def create_engine(self, url: str):
        raise NotImplementedError
