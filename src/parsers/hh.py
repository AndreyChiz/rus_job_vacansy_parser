from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
from playwright.async_api import BrowserContext

from core.schema import VacancyDTO
from core.base.base_parser import BaseVacancyParser


class HHParser(BaseVacancyParser):
    def _base_query(self) -> Dict[str, Any]:
        return {
            "hhtmFrom": "vacancy_search_list",
            "hhtmFromLabel": "old_filter",
            "search_field": [
                "name",
                "company_name",
                "description",
            ],
            "enable_snippets": "false",
            "hhtmSource": "vacancy_search_list",
            "hhtmSourceLabel": "vacancy_search_list",
            # "work_format": [
            #     "REMOTE",
            #     "HYBRID",
            # ],
            "L_save_area": "true",
        }

    def _build_url(self) -> str:
        params = self._base_query()
        params["text"] = self.query
        query_string = urlencode(params, doseq=True)
        return f"{self.base_url}?{query_string}"

    def _get_card_id_from_url(self, url:str) -> str: 
        return url.split("/")[-1].split("?")[0]


    async def search_cards(self, context: BrowserContext) -> List[str]:
        page = await context.new_page()

        try:
            await page.goto(self._build_url(), wait_until="domcontentloaded")

            await page.wait_for_selector(
                "[data-qa='vacancy-serp__vacancy'], "
                "[data-qa='vacancy-card'], "
                ".serp-item"
            )

            cards = await page.query_selector_all(
                "[data-qa='vacancy-serp__vacancy'], "
                "[data-qa='vacancy-card'], "
                ".serp-item"
            )

            urls: List[str] = []

            for card in cards[: self.card_parse_limit]:
                link_el = await card.query_selector("a")
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

            await page.wait_for_selector("[data-qa='vacancy-title']")

            title = await page.inner_text("[data-qa='vacancy-title']")

            employer = None
            salary = None
            description = None
            experience = None

            employer_el = await page.query_selector("[data-qa='vacancy-company-name']")
            if employer_el:
                employer = await employer_el.inner_text()

            salary_el = await page.query_selector("[data-qa='vacancy-salary']")
            if salary_el:
                salary = await salary_el.inner_text()

            desc_el = await page.query_selector("[data-qa='vacancy-description']")
            if desc_el:
                description = await desc_el.inner_text()

            exp_el = await page.query_selector("[data-qa='vacancy-experience']")
            if exp_el:
                experience = await exp_el.inner_text()

            vacancy_id = url.split("/")[-1].split("?")[0]

            return VacancyDTO(
                url=url,
                vacancy_id=vacancy_id,
                title=title,
                employer=employer,
                salary=salary,
                experience=experience,
                description=description,
            )

        except Exception:
            return None

        finally:
            await page.close()