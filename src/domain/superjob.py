from typing import Dict, Any, List, Optional
from urllib.parse import urlencode

from playwright.async_api import BrowserContext

from core.schema import VacancyDTO
from core.base.base_parser import BaseVacancyParser


class SuperJobParser(BaseVacancyParser):
    def _base_query(self) -> Dict[str, Any]:
        return {
            "keywords": self.query,
            "without_resume_send_on_vacancy": 1,
            "noGeo": 1,
            "click_from": "facet",
        }

    def _build_url(self) -> str:
        query_string = urlencode(self._base_query(), doseq=True)
        return f"{self.base_url}/?{query_string}"

    def _get_card_id_from_url(self, url:str) -> str: 
        return url.rstrip("/").split("/")[-1].replace(".html", "").split("?")[0].split("-")[-1]


    async def search_cards(self, context: BrowserContext) -> List[str]:
        page = await context.new_page()

        try:
            await page.goto(self._build_url(), wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_selector("a[href*='/vakansii/']", state="attached", timeout=10000)

            links = await page.query_selector_all("a[href*='/vakansii/']")

            urls: List[str] = []
            seen: set[str] = set()

            for link in links:
                href = await link.get_attribute("href")

                if not href:
                    continue

                if not href.startswith("http"):
                    href = f"https://{self.host}{href}"

                if "/vakansii/" not in href:
                    continue

                if not href.endswith(".html"):
                    continue

                if "vacancy/search" in href:
                    continue

                vacancy_id = href.rstrip("/").split("/")[-1].replace(".html", "").split("?")[0]

                if vacancy_id in seen:
                    continue

                seen.add(vacancy_id)
                urls.append(href)

                if len(urls) >= self.card_parse_limit:
                    break

            return urls

        finally:
            await page.close()

    async def _get_card_details(self, context: BrowserContext, url: str) -> Optional[VacancyDTO]:
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(2000)

            title = None
            title_el = await page.query_selector("h1")
            if title_el:
                title = (await title_el.inner_text()).strip()

            employer = None
            employer_el = await page.query_selector("a[href*='/clients/'], [class*='company'], [class*='Client']")
            if employer_el:
                employer = (await employer_el.inner_text()).strip()

            salary = None
            salary_el = await page.query_selector("[class*='salary'], span[class*='salary'], [data-qa*='salary']")
            if salary_el:
                salary = (await salary_el.inner_text()).strip()

            description = None
            desc_el = await page.query_selector("span.mrLsm > span")

            if desc_el:
                text = await desc_el.inner_text()
                if text and text.strip():
                    description = text.strip()

            if not description:
                desc_el = await page.query_selector("span.mrLsm")
                if desc_el:
                    text = await desc_el.inner_text()
                    if text and text.strip():
                        description = text.strip()

            if description:
                description = " ".join(description.split())

            experience = None
            page_text = await page.inner_text("body")

            if "опыт" in page_text.lower():
                experience = "mentioned_in_description"

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