import asyncio
from typing import List
from logging import getLogger

from core.schema import VacancyDTO

logger = getLogger(__name__)


class ParseVacanciesUseCase:
    def __init__(self, parsers, browser, cache, on_vacancy=None):
        self.parsers = parsers
        self.browser = browser
        self.cache = cache
        self.on_vacancy = on_vacancy

    async def execute(self, hosts: List[str] | None = None, query: str | None = None, on_vacancy=None) -> List[VacancyDTO]:
        parsers = self._filter_parsers(hosts, query)
        self.on_vacancy = on_vacancy

        tasks = [self._run_parser(parser) for parser in parsers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        vacancies = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("Parser failed: %s", result)
            elif isinstance(result, list):
                vacancies.extend(result)

        return vacancies

    def _filter_parsers(self, hosts: List[str] | None, query: str | None):
        parsers = self.parsers

        if hosts:
            parsers = [p for p in parsers if p.host in hosts]

        if query:
            for parser in parsers:
                parser.query = query

        return parsers

    async def _run_parser(self, parser) -> List[VacancyDTO]:
        context = await self.browser.new_context()

        try:
            urls = await parser.search_cards(context)

            filtered_urls = []
            seen = 0
            fresh = 0

            for url in urls:
                vacancy_id = parser._get_card_id_from_url(url)

                if await self.cache.sismember("vacancy:processed", vacancy_id):
                    seen += 1
                    continue

                fresh += 1
                filtered_urls.append(url)

            logger.info(
                "[%s] Found %d cards. New: %d, Cached: %d",
                parser.host,
                len(urls),
                fresh,
                seen,
            )

            async def on_vacancy(vacancy: VacancyDTO):
                await self.cache.sadd("vacancy:processed", vacancy.vacancy_id)
                if self.on_vacancy:
                    await self.on_vacancy(vacancy)

            vacancies = await parser.parse_cards(context, filtered_urls, on_vacancy=on_vacancy)

            logger.info(
                "[%s] Parsed %d vacancies", parser.host, len(vacancies)
            )

            return vacancies

        except Exception as e:
            logger.error("[%s] Search failed: %s", parser.host, e)
            return []

        finally:
            await context.close()
