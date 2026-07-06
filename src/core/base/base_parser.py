from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import asyncio
from playwright.async_api import BrowserContext
from core.schema import VacancyDTO
import logging




class BaseVacancyParser(ABC):
    def __init__(
        self,
        base_url: str,
        host: str,
        query: str,
        parallel: int = 5,
        card_parse_limit: int = 10,
    ):
        self.base_url = base_url
        self.host = host
        self.query = query
        self.parallel = parallel
        self.card_parse_limit = card_parse_limit
        self.logger = logging.getLogger(self.__class__.__module__)

    def logger_info(self) -> dict:
        return {
            "parser": self.__class__.__name__,
            "host": self.host,
            "url": self._build_url(),
            "parallel": self.parallel,
            "card_parse_limit": self.card_parse_limit,
        }

    @abstractmethod
    def _base_query(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def _build_url(self) -> str:
        pass
    
    
    @abstractmethod # TODO может метод класса? (состояния нет)
    def _get_card_id_from_url(self, url:str) -> str: # TODO: может все под ->int: ?!
        pass

    @abstractmethod
    async def search_cards(self, context: BrowserContext) -> List[str]:
        pass

    @abstractmethod
    async def _get_card_details(
        self,
        context: BrowserContext,
        url: str,
    ) -> Optional[VacancyDTO]:
        pass

    
    async def parse_cards(
        self,
        context: BrowserContext,
        urls: List[str],
    ) -> List[VacancyDTO]:

        sem = asyncio.Semaphore(self.parallel)

        async def worker(url: str):
            async with sem:
                try:
                    return await self._get_card_details(context, url)
                except Exception:
                    return None

        results = await asyncio.gather(*[
            worker(url)
            for url in urls
        ])

        return [v for v in results if v]