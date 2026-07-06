from typing import Dict, Any, List, Optional

from urllib.parse import urlencode

from playwright.async_api import BrowserContext

from core.schema import VacancyDTO
from core.base.base_parser import BaseVacancyParser


class HabrParser(BaseVacancyParser):

    def _base_query(self) -> Dict[str, Any]:
        return {
            "q": self.query,
            # "remote": "true",
            "sort": "date",
            "type": "all",
        }

    def _build_url(self) -> str:
        params = self._base_query()
        query_string = urlencode(params)
        return f"{self.base_url}?{query_string}"

        
    def _get_card_id_from_url(self, url:str) -> str: 
        return url.split("/")[-1].split("?")[0]

    async def search_cards(self, context: BrowserContext) -> List[str]:
        page = await context.new_page()

        try:
            await page.goto(self._build_url(), wait_until="domcontentloaded")

            await page.wait_for_selector(".vacancy-card")

            cards = await page.query_selector_all(".vacancy-card")

            urls: List[str] = []

            for card in cards[: self.card_parse_limit]:
                link_el = await card.query_selector(".vacancy-card__title a")
                if not link_el:
                    continue

                href = await link_el.get_attribute("href")
                if not href:
                    continue

                if not href.startswith("http"):
                    href = f"https://{self.host}{href}"

                urls.append(href)

            return urls

        finally:
            await page.close()

    async def _get_card_details(
        self,
        context: BrowserContext,
        url: str,
    ) -> Optional[VacancyDTO]:

        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded")

            await page.wait_for_selector("h1.page-title__title")

            title = await page.inner_text("h1.page-title__title")

            salary = None
            salary_el = await page.query_selector(
                ".vacancy-header__salary .basic-salary"
            )
            if salary_el:
                salary = await salary_el.inner_text()

            employer = None
            employer_el = await page.query_selector(
                ".section.company_info .company_name a"
            )
            if employer_el:
                employer = await employer_el.inner_text()

            description = None
            desc_el = await page.query_selector(
                ".vacancy-description__text .style-ugc"
            )
            if desc_el:
                description = await desc_el.inner_text()

            vacancy_id = self._get_card_id_from_url(url)

            return VacancyDTO(
                url=url,
                vacancy_id=vacancy_id,
                host=self.host,
                title=title,
                employer=employer,
                salary=salary,
                experience=None,
                description=description,
            )

        except Exception:
            return None

        finally:
            await page.close()