import asyncio
from logging import getLogger

logger = getLogger(__name__)


class ParseVacanciesUseCase:
    def __init__(self, parsers, browser, cache):
        self.parsers = parsers
        self.browser = browser
        self.cache = cache

    async def execute(self) -> bool:
        acquired = await self.cache.set_nx("vacancy:parser:running", "1", ttl=600)
        if not acquired:
            logger.warning("Parser already running, skipping")
            return False

        try:
            tasks = [self._run_parser(parser) for parser in self.parsers]
            await asyncio.gather(*tasks)
        finally:
            await self.cache.delete("vacancy:parser:running")

        return True

    async def _run_parser(self, parser):
        context = await self.browser.new_context()

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

            for vacancy in vacancies:
                await self.cache.rpush("vacancy:queue", vacancy.model_dump_json())
                await self.cache.sadd("vacancy:processed", vacancy.vacancy_id)

            logger.info(
                "[%s] Pushed %d vacancies to queue", parser.host, len(vacancies)
            )

        finally:
            await context.close()
