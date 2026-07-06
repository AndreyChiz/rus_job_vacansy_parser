import asyncio
from typing import List
from logging import getLogger

from core.schema import VacancyDTO

logger = getLogger(__name__)


class ParseVacanciesUseCase:
    def __init__(self, parsers, browser, cache):
        self.parsers = parsers
        self.browser = browser
        self.cache = cache

    async def execute(self, hosts: List[str] | None = None, query: str | None = None) -> List[VacancyDTO]:
        parsers = self._filter_parsers(hosts, query)

        tasks = [self._run_parser(parser) for parser in parsers]
        results = await asyncio.gather(*tasks)
        return [v for batch in results for v in batch]

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

            vacancies = await parser.parse_cards(context, filtered_urls)

            for vacancy in vacancies:
                await self.cache.sadd("vacancy:processed", vacancy.vacancy_id)

            logger.info(
                "[%s] Parsed %d vacancies", parser.host, len(vacancies)
            )

            return vacancies

        finally:
            await context.close()
