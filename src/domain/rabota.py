from typing import Dict, Any, List, Optional
from urllib.parse import urlencode

from playwright.async_api import BrowserContext

from core.schema import VacancyDTO
from core.base.base_parser import BaseVacancyParser
from urllib.parse import urlparse

class RabotaParser(BaseVacancyParser):

    def _base_query(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "location.kind": "region",
            "location.radius": "any",
            "location.name": "Россия",
        }

    def _build_url(self) -> str:
        params = self._base_query()
        return f"{self.base_url}?{urlencode(params, doseq=True)}"

    def _get_card_id_from_url(self, url: str) -> str:
        path = urlparse(url).path.rstrip("/")
        return path.split("/vacancy/")[-1]

    async def search_cards(self, context: BrowserContext) -> List[str]:
        page = await context.new_page()

        try:
            await page.goto(self._build_url(), wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            links = await page.query_selector_all("a[href*='/vacancy/']")

            urls: List[str] = []
            seen: set[str] = set()

            for link in links[: self.card_parse_limit]:
                href = await link.get_attribute("href")
                if not href:
                    continue

                if not href.startswith("http"):
                    href = f"https://{self.host}{href}"

                vacancy_id = self._get_card_id_from_url(href)

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
            await page.wait_for_timeout(3000)

            title = None
            title_el = await page.query_selector(
                "h1.vacancy-card__title, h1[itemprop='title']"
            )
            if title_el:
                title = (await title_el.inner_text()).strip()

            salary = None
            salary_el = await page.query_selector(
                ".vacancy-card__salary, h3.vacancy-card__salary"
            )
            if salary_el:
                salary = (await salary_el.inner_text()).strip()

            employer = None
            employer_el = await page.query_selector(
                "a[itemprop='legalName'], .verified-employer + a"
            )
            if employer_el:
                employer = (await employer_el.inner_text()).strip()

            description = None
            desc_el = await page.query_selector("[itemprop='description']")

            if desc_el:
                description = (await desc_el.inner_text()).strip()
            else:
                raw_el = await page.query_selector(".vacancy-card__description")
                if raw_el:
                    raw = await raw_el.inner_text()

                    for bad in [
                        "Задайте вопрос работодателю",
                        "Он получит его вместе с откликом",
                        "Адрес",
                        "Вакансия размещена",
                    ]:
                        raw = raw.replace(bad, "")

                    description = raw.strip()

            experience = None
            if description and "опыт" in description.lower():
                experience = "mentioned_in_description"

            # ✅ ЕДИНСТВЕННЫЙ ИСТОЧНИК ID (URL ONLY)
            vacancy_id = self._get_card_id_from_url(url)

            return VacancyDTO(
                url=url,
                vacancy_id=vacancy_id,
                host=self.host,
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