from core.base.base_vacancy_reposytory import BaseVacancyRepository
from infra.browser import BrowserProvider
from infra.cache import CacheProvider
from infra.database.database_provider import DatabaseProvider

from core.vacancy_reposytory import vacancy_repository_factory

from parsers.hh import HHParser
from parsers.habr import HabrParser
from parsers.rabota import RabotaParser
from parsers.superjob import SuperJobParser
from parsers.zarplata import ZarplataParser

from app.usecases.update_vacancies import UpdateVacanciesUseCase
from app.usecases.get_vacancies import GetVacanciesUseCase

from config import (
    CACHE_TYPE,
    CACHE_URL,
    DATABASE_URL,
    DATABASE_TYPE,
    BROWSER_ENGINE_TYPE,
    PARALLEL_WORKERS,
    CARDS_PARSE_LIMIT,
    PARSER_QUERY_WORDS,
)


class Lifespan:
    def __init__(self, browser, cache, database):
        self.browser = browser
        self.cache = cache
        self.database = database

    async def start(self) -> None:
        await self.database.start()
        await self.browser.start()
        await self.cache.start()

    async def stop(self) -> None:
        await self.cache.stop()
        await self.browser.stop()
        await self.database.stop()


class Container:
    def __init__(self):

        self.database = DatabaseProvider(
            db_type=DATABASE_TYPE,
            url=DATABASE_URL,
        )

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
            database=self.database,
        )

        self.vacancy_repository: BaseVacancyRepository | None = None

    def get_browser(self):
        return self.browser.get_instance()

    def get_cache(self):
        return self.cache.get_instance()

    def get_vacancy_repository(self):
        return vacancy_repository_factory(
            database=self.database,
        )

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

    def update_usecase(self):
        return UpdateVacanciesUseCase(
            parsers=self.get_parsers(),
            repository=self.get_vacancy_repository(),
            browser=self.get_browser(),
            cache=self.get_cache(),
        )
