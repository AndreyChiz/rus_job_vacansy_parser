#!/usr/bin/env python3
import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from domain.hh import HHParser
from domain.habr import HabrParser
from domain.rabota import RabotaParser
from domain.superjob import SuperJobParser
from domain.zarplata import ZarplataParser
from core.schema import VacancyDTO

QUERY = "Python"
LIMIT = 3


async def test_parser(parser, context, label):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    try:
        urls = await parser.search_cards(context)
        print(f"  [search_cards] Найдено: {len(urls)} URL")
        for u in urls[:2]:
            print(f"    {u[:90]}")
    except Exception as e:
        print(f"  [search_cards] ОШИБКА: {e}")
        return []

    if not urls:
        print(f"  [!] Нет URL для парсинга")
        return []

    filtered = urls[:LIMIT]
    vacancies = await parser.parse_cards(context, filtered)
    print(f"  [parse_cards] Спарсено: {len(vacancies)} вакансий")

    errors = []
    for v in vacancies:
        url = v.url
        vid = v.vacancy_id
        host = v.host

        if host == "hh.ru":
            expected = url.split("/vacancy/")[-1].split("?")[0]
            if vid != expected:
                errors.append(f"  ID mismatch: url_id={expected}, field_id={vid}")

        elif host == "career.habr.com":
            expected = url.split("/")[-1].split("?")[0]
            if vid != expected:
                errors.append(f"  ID mismatch: url_id={expected}, field_id={vid}")

        elif host == "russia.superjob.ru":
            slug_part = url.rstrip("/").split("/")[-1].replace(".html", "")
            expected = slug_part.split("-")[-1]
            if vid != expected:
                errors.append(f"  ID mismatch: url_id={expected}, field_id={vid}")

        elif host == "www.rabota.ru":
            from urllib.parse import urlparse
            path = urlparse(url).path.rstrip("/")
            expected = path.split("/vacancy/")[-1]
            if vid != expected:
                errors.append(f"  ID mismatch: url_id={expected}, field_id={vid}")

        elif host == "zarplata.ru":
            expected = url.rstrip("/").split("/")[-1].split("?")[0]
            if vid != expected:
                errors.append(f"  ID mismatch: url_id={expected}, field_id={vid}")

    if errors:
        print(f"  [✗] ОШИБКИ ID ({len(errors)}):")
        for e in errors:
            print(e)
    else:
        print(f"  [✓] Все ID корректны")

    for i, v in enumerate(vacancies, 1):
        print(f"\n  --- #{i} ---")
        print(f"  ID:       {v.vacancy_id}")
        print(f"  Title:    {(v.title or 'N/A')[:60]}")
        print(f"  Employer: {(v.employer or 'N/A')[:40]}")
        print(f"  Salary:   {(v.salary or 'N/A')[:40]}")
        print(f"  URL:      {v.url[:90]}")

    return vacancies


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
            ],
        )

        all_vacancies = []

        parsers = [
            ("hh.ru", HHParser(
                base_url="https://hh.ru/search/vacancy",
                host="hh.ru",
                query=QUERY,
                parallel=2,
                card_parse_limit=LIMIT,
            )),
            ("career.habr.com", HabrParser(
                base_url="https://career.habr.com/vacancies",
                host="career.habr.com",
                query=QUERY,
                parallel=2,
                card_parse_limit=LIMIT,
            )),
            ("www.rabota.ru", RabotaParser(
                base_url="https://www.rabota.ru/vacancy",
                host="www.rabota.ru",
                query=QUERY,
                parallel=2,
                card_parse_limit=LIMIT,
            )),
            ("russia.superjob.ru", SuperJobParser(
                base_url="https://russia.superjob.ru/vacancy/search",
                host="russia.superjob.ru",
                query=QUERY,
                parallel=2,
                card_parse_limit=LIMIT,
            )),
            ("zarplata.ru", ZarplataParser(
                base_url="https://zarplata.ru/vacancy",
                host="zarplata.ru",
                query=QUERY,
                parallel=2,
                card_parse_limit=LIMIT,
            )),
        ]

        for host, parser in parsers:
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                locale="ru-RU",
            )
            stealth = Stealth()
            await stealth.apply_stealth_async(context)

            try:
                vacancies = await test_parser(parser, context, f"Парсер: {host}")
                all_vacancies.extend(vacancies)
            except Exception as e:
                print(f"\n  [FATAL] {host}: {e}")
            finally:
                await context.close()

        await browser.close()

    print(f"\n{'='*60}")
    print(f"  ИТОГО: {len(all_vacancies)} вакансий из {len(set(v.host for v in all_vacancies))} парсеров")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
