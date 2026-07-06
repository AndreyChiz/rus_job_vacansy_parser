from typing import Dict, Any, List, Optional
from urllib.parse import urlencode

from playwright.async_api import BrowserContext

from core.schema import VacancyDTO
from core.base.base_parser import BaseVacancyParser


class ZarplataParser(BaseVacancyParser):
    def _base_query(self) -> Dict[str, Any]:
        return {
            "text": self.query,
            # "remote": "true",
        }

    def _build_url(self) -> str:
        params = self._base_query()
        query_string = urlencode(params)
        return f"{self.base_url}?{query_string}"

    def _get_card_id_from_url(self, url:str) -> str:
        return url.rstrip("/").split("/")[-1].split("?")[0]

    async def search_cards(self, context: BrowserContext) -> List[str]:
        page = await context.new_page()

        try:
            await page.goto(self._build_url(), wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            cards = await page.query_selector_all(
                "[data-qa='vacancy-serp__vacancy'], .vacancy-card"
            )

            urls: List[str] = []
            seen: set[str] = set()

            for card in cards[: self.card_parse_limit]:
                link_el = await card.query_selector("a")
                if not link_el:
                    continue

                href = await link_el.get_attribute("href")
                if not href:
                    continue

                if not href.startswith("http"):
                    href = f"https://{self.host}{href}"

                vacancy_id = href.rstrip("/").split("/")[-1].split("?")[0]
                if vacancy_id in seen:
                    continue
                seen.add(vacancy_id)
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
            await page.wait_for_timeout(4000)

            title_el = await page.query_selector("h1")
            title = (await title_el.inner_text()).strip() if title_el else None

            employer_el = await page.query_selector("[data-qa='vacancy-company__details']")
            employer = (await employer_el.inner_text()).strip() if employer_el else None

            salary_el = await page.query_selector("[data-qa='vacancy-salary']")
            salary = (await salary_el.inner_text()).strip() if salary_el else None

            exp_el = await page.query_selector(".vacancy-experience")
            experience = (await exp_el.inner_text()).strip() if exp_el else None

            desc_el = await page.query_selector(
                ".vacancy-description, [data-qa='vacancy-description']"
            )
            description = (await desc_el.inner_text()).strip() if desc_el else None

            vacancy_id = self._get_card_id_from_url(url)

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