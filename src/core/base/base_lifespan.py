from abc import ABC, abstractmethod


class BaseLifecycle(ABC):
    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...