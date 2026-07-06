import asyncio
from typing import List, Dict
from logging import getLogger

from core.schema import VacancyDTO

logger = getLogger(__name__)


class UpdateVacanciesUseCase:
    def __init__(self, parsers, repository, browser, cache):
        self.parsers = parsers
        self.vacancy_repository = repository
        self.browser = browser
        self.cache = cache

    async def execute(self) -> Dict[str, List[VacancyDTO]]:

        tasks = [self._run_parser(parser, self.browser) for parser in self.parsers]

        parser_configs = [
            f"{p.__class__.__name__}: {p.logger_info()}" for p in self.parsers
        ]
        logger.info(
            "Starting update process.\nParsers config:\n%s", "\n".join(parser_configs)
        )

        results = await asyncio.gather(*tasks)

        aggregated_vacancies = {
            host: data for result in results for host, data in result.items()
        }

        all_ids = [
            vacancy.vacancy_id
            for vacancies in aggregated_vacancies.values()
            for vacancy in vacancies
        ]

        logger.info("Total new vacancies found: %d", len(all_ids))
        if all_ids:
            logger.debug("New vacancy IDs: %s", all_ids)

        await self.vacancy_repository.save_many(aggregated_vacancies)

        marked = 0

        for vacancies in aggregated_vacancies.values():
            for vacancy in vacancies:
                await self.cache.sadd("vacancy:processed", vacancy.vacancy_id)

                marked += 1

        return aggregated_vacancies

    async def _run_parser(self, parser, browser):

        context = await browser.new_context()

        try:
            urls = await parser.search_cards(context)

            filtered_urls = []

            seen = 0
            fresh = 0

            for url in urls:
                vacancy_id = parser._get_card_id_from_url(url)

                already_seen = await self.cache.sismember(
                    "vacancy:processed", vacancy_id
                )

                if already_seen:
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

            logger.info(
                "[%s] Successfully parsed %d vacancies", parser.host, len(vacancies)
            )

            return {parser.host: vacancies}

        finally:
            await context.close()
