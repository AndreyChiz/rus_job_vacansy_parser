from infra.browser import BrowserProvider
from infra.cache import CacheProvider

from domain.hh import HHParser
from domain.habr import HabrParser
from domain.rabota import RabotaParser
from domain.superjob import SuperJobParser
from domain.zarplata import ZarplataParser

from app.usecases.parse_vacancies import ParseVacanciesUseCase

from config import (
    CACHE_TYPE,
    CACHE_URL,
    BROWSER_ENGINE_TYPE,
    PARALLEL_WORKERS,
    CARDS_PARSE_LIMIT,
    PARSER_QUERY_WORDS,
)


class Lifespan:
    def __init__(self, browser, cache):
        self.browser = browser
        self.cache = cache

    async def start(self) -> None:
        await self.cache.start()
        await self.browser.start()

    async def stop(self) -> None:
        await self.browser.stop()
        await self.cache.stop()


class Container:
    def __init__(self):

        self.browser = BrowserProvider(
            BROWSER_ENGINE_TYPE,
        )

        self.cache = CacheProvider(
            cache_type=CACHE_TYPE,
            url=CACHE_URL,
        )

        self.lifespan = Lifespan(
            browser=self.browser,
            cache=self.cache,
        )

    def get_browser(self):
        return self.browser.get_instance()

    def get_cache(self):
        return self.cache.get_instance()

    def get_parsers(self):
        return [
            HHParser(
                base_url="https://hh.ru/search/vacancy",
                host="hh.ru",
                query=PARSER_QUERY_WORDS,
                parallel=PARALLEL_WORKERS,
                card_parse_limit=CARDS_PARSE_LIMIT,
            ),
            HabrParser(
                base_url="https://career.habr.com/vacancies",
                host="career.habr.com",
                query=PARSER_QUERY_WORDS,
                parallel=PARALLEL_WORKERS,
                card_parse_limit=CARDS_PARSE_LIMIT,
            ),
            RabotaParser(
                base_url="https://www.rabota.ru/vacancy",
                host="www.rabota.ru",
                query=PARSER_QUERY_WORDS,
                parallel=PARALLEL_WORKERS,
                card_parse_limit=CARDS_PARSE_LIMIT,
            ),
            SuperJobParser(
                base_url="https://russia.superjob.ru/vacancy/search",
                host="russia.superjob.ru",
                query=PARSER_QUERY_WORDS,
                parallel=PARALLEL_WORKERS,
                card_parse_limit=CARDS_PARSE_LIMIT,
            ),
            ZarplataParser(
                base_url="https://zarplata.ru/vacancy",
                host="zarplata.ru",
                query=PARSER_QUERY_WORDS,
                parallel=PARALLEL_WORKERS,
                card_parse_limit=CARDS_PARSE_LIMIT,
            ),
        ]

    def parse_usecase(self):
        return ParseVacanciesUseCase(
            parsers=self.get_parsers(),
            browser=self.get_browser(),
            cache=self.get_cache(),
        )
