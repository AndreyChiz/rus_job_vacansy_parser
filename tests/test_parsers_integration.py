import pytest
from unittest.mock import AsyncMock

from core.schema import VacancyDTO
from domain.hh import HHParser
from domain.habr import HabrParser
from domain.rabota import RabotaParser
from domain.superjob import SuperJobParser
from domain.zarplata import ZarplataParser


def make_mock_element(text="Test text"):
    el = AsyncMock()
    el.inner_text = AsyncMock(return_value=text)
    el.get_attribute = AsyncMock(return_value="https://example.com")
    return el


def make_mock_page_with_cards(cards_data):
    page = AsyncMock()

    card_elements = []
    for card in cards_data:
        card_el = AsyncMock()
        link_el = AsyncMock()
        link_el.get_attribute = AsyncMock(return_value=card["url"])
        card_el.query_selector = AsyncMock(return_value=link_el)
        card_elements.append(card_el)

    page.query_selector_all = AsyncMock(return_value=card_elements)
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.close = AsyncMock()
    return page


def make_mock_page_with_details(details):
    page = AsyncMock()

    title = details.get("title", "No title")
    employer = details.get("employer", "Unknown")
    salary = details.get("salary", "")
    experience = details.get("experience", "")
    description = details.get("description", "No description")

    title_selectors = [
        "[data-qa='vacancy-title']",
        "h1.page-title__title",
        "h1.vacancy-card__title",
        "h1[itemprop='title']",
        "h1",
    ]
    employer_selectors = [
        "[data-qa='vacancy-company-name']",
        ".section.company_info .company_name a",
        "[data-qa='vacancy-company__details']",
        "a[itemprop='legalName']",
        ".verified-employer + a",
        "a[href*='/clients/']",
        "[class*='company']",
        "[class*='Client']",
        ".vacancy-card__company a",
        "a[href*='/companies/']",
    ]
    salary_selectors = [
        "[data-qa='vacancy-salary']",
        ".vacancy-header__salary .basic-salary",
        ".vacancy-card__salary",
        "h3.vacancy-card__salary",
        ".basic-salary",
    ]
    experience_selectors = [
        "[data-qa='vacancy-experience']",
        ".vacancy-experience",
    ]
    description_selectors = [
        "[data-qa='vacancy-description']",
        ".vacancy-description__text .style-ugc",
        ".vacancy-description__text",
        ".vacancy-description",
        "[itemprop='description']",
        ".vacancy-card__description",
        "span.mrLsm > span",
        "span.mrLsm",
    ]

    selector_value_map = {}
    for sel in title_selectors:
        selector_value_map[sel] = title
    for sel in employer_selectors:
        selector_value_map[sel] = employer
    for sel in salary_selectors:
        selector_value_map[sel] = salary
    for sel in experience_selectors:
        selector_value_map[sel] = experience
    for sel in description_selectors:
        selector_value_map[sel] = description

    combined_selectors = [
        "h1.vacancy-card__title, h1[itemprop='title']",
        ".vacancy-card__salary, h3.vacancy-card__salary",
        "a[itemprop='legalName'], .verified-employer + a",
        ".vacancy-description, [data-qa='vacancy-description']",
    ]
    for sel in combined_selectors:
        if sel not in selector_value_map:
            parts = [s.strip() for s in sel.split(",")]
            for part in parts:
                if part in selector_value_map:
                    selector_value_map[sel] = selector_value_map[part]
                    break

    async def mock_query_selector(selector):
        val = selector_value_map.get(selector)
        if val is not None:
            return make_mock_element(val)
        parts = [s.strip() for s in selector.split(",")]
        for part in parts:
            val = selector_value_map.get(part)
            if val is not None:
                return make_mock_element(val)
        return None

    async def mock_inner_text(selector=None):
        if selector is None:
            return description
        return selector_value_map.get(selector, description)

    page.query_selector = AsyncMock(side_effect=mock_query_selector)
    page.inner_text = AsyncMock(side_effect=mock_inner_text)
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.close = AsyncMock()
    return page


class TestHHParserIntegration:
    @pytest.mark.asyncio
    async def test_search_cards_with_links(self):
        parser = HHParser(
            base_url="https://hh.ru/search/vacancy",
            host="hh.ru",
            query="Python",
            parallel=4,
            card_parse_limit=10,
        )

        cards_data = [
            {"url": "https://hh.ru/vacancy/111111?from=direct"},
            {"url": "https://hh.ru/vacancy/222222?from=direct"},
            {"url": "https://hh.ru/vacancy/333333"},
        ]

        context = AsyncMock()
        mock_page = make_mock_page_with_cards(cards_data)
        context.new_page = AsyncMock(return_value=mock_page)

        urls = await parser.search_cards(context)

        assert len(urls) == 3
        assert "https://hh.ru/vacancy/111111?from=direct" in urls
        assert "https://hh.ru/vacancy/222222?from=direct" in urls
        assert "https://hh.ru/vacancy/333333" in urls

    @pytest.mark.asyncio
    async def test_search_cards_respects_limit(self):
        parser = HHParser(
            base_url="https://hh.ru/search/vacancy",
            host="hh.ru",
            query="Python",
            parallel=4,
            card_parse_limit=2,
        )

        cards_data = [
            {"url": "https://hh.ru/vacancy/111111"},
            {"url": "https://hh.ru/vacancy/222222"},
            {"url": "https://hh.ru/vacancy/333333"},
        ]

        context = AsyncMock()
        mock_page = make_mock_page_with_cards(cards_data)
        context.new_page = AsyncMock(return_value=mock_page)

        urls = await parser.search_cards(context)

        assert len(urls) == 2

    @pytest.mark.asyncio
    async def test_get_card_details(self):
        parser = HHParser(
            base_url="https://hh.ru/search/vacancy",
            host="hh.ru",
            query="Python",
            parallel=4,
            card_parse_limit=10,
        )

        details = {
            "title": "Python Developer",
            "employer": "Yandex",
            "salary": "150000-200000 руб.",
            "experience": "1-3 года",
            "description": "Ищем Python разработчика",
        }

        context = AsyncMock()
        mock_page = make_mock_page_with_details(details)
        context.new_page = AsyncMock(return_value=mock_page)

        vacancy = await parser._get_card_details(context, "https://hh.ru/vacancy/111111")

        assert vacancy is not None
        assert vacancy.title == "Python Developer"
        assert vacancy.employer == "Yandex"
        assert vacancy.salary == "150000-200000 руб."
        assert vacancy.vacancy_id == "111111"


class TestHabrParserIntegration:
    @pytest.mark.asyncio
    async def test_search_cards_with_links(self):
        parser = HabrParser(
            base_url="https://career.habr.com/vacancies",
            host="career.habr.com",
            query="Python",
            parallel=4,
            card_parse_limit=10,
        )

        cards_data = [
            {"url": "https://career.habr.com/vacancies/444444"},
            {"url": "https://career.habr.com/vacancies/555555"},
        ]

        context = AsyncMock()
        mock_page = make_mock_page_with_cards(cards_data)
        context.new_page = AsyncMock(return_value=mock_page)

        urls = await parser.search_cards(context)

        assert len(urls) == 2
        assert "https://career.habr.com/vacancies/444444" in urls
        assert "https://career.habr.com/vacancies/555555" in urls

    @pytest.mark.asyncio
    async def test_get_card_details(self):
        parser = HabrParser(
            base_url="https://career.habr.com/vacancies",
            host="career.habr.com",
            query="Python",
            parallel=4,
            card_parse_limit=10,
        )

        details = {
            "title": "Senior Python Developer",
            "employer": "VK",
            "salary": "200000-300000 руб.",
            "description": "Ищем опытного Python разработчика",
        }

        context = AsyncMock()
        mock_page = make_mock_page_with_details(details)
        context.new_page = AsyncMock(return_value=mock_page)

        vacancy = await parser._get_card_details(context, "https://career.habr.com/vacancies/444444")

        assert vacancy is not None
        assert vacancy.title == "Senior Python Developer"
        assert vacancy.employer == "VK"
        assert vacancy.vacancy_id == "444444"


class TestRabotaParserIntegration:
    @pytest.mark.asyncio
    async def test_search_cards_with_links(self):
        parser = RabotaParser(
            base_url="https://www.rabota.ru/vacancy",
            host="www.rabota.ru",
            query="Python",
            parallel=4,
            card_parse_limit=10,
        )

        link1 = AsyncMock()
        link1.get_attribute = AsyncMock(return_value="https://www.rabota.ru/vacancy/666666")
        link2 = AsyncMock()
        link2.get_attribute = AsyncMock(return_value="https://www.rabota.ru/vacancy/777777")

        links = [link1, link2]

        context = AsyncMock()
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=links)
        mock_page.close = AsyncMock()
        context.new_page = AsyncMock(return_value=mock_page)

        urls = await parser.search_cards(context)

        assert len(urls) == 2
        assert "https://www.rabota.ru/vacancy/666666" in urls
        assert "https://www.rabota.ru/vacancy/777777" in urls

    @pytest.mark.asyncio
    async def test_get_card_details(self):
        parser = RabotaParser(
            base_url="https://www.rabota.ru/vacancy",
            host="www.rabota.ru",
            query="Python",
            parallel=4,
            card_parse_limit=10,
        )

        details = {
            "title": "Python Developer",
            "employer": "Sber",
            "salary": "180000 руб.",
            "experience": "3-6 лет",
            "description": "Требуется Python разработчик",
        }

        context = AsyncMock()
        mock_page = make_mock_page_with_details(details)
        context.new_page = AsyncMock(return_value=mock_page)

        vacancy = await parser._get_card_details(context, "https://www.rabota.ru/vacancy/666666")

        assert vacancy is not None
        assert vacancy.title == "Python Developer"
        assert vacancy.vacancy_id == "666666"


class TestSuperJobParserIntegration:
    @pytest.mark.asyncio
    async def test_search_cards_with_links(self):
        parser = SuperJobParser(
            base_url="https://russia.superjob.ru/vacancy/search",
            host="russia.superjob.ru",
            query="Python",
            parallel=4,
            card_parse_limit=10,
        )

        links = [
            AsyncMock(get_attribute=AsyncMock(return_value="https://russia.superjob.ru/vakansii/python-razrabotchik-888888.html")),
            AsyncMock(get_attribute=AsyncMock(return_value="https://russia.superjob.ru/vakansii/python-dev-999999.html")),
        ]

        context = AsyncMock()
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=links)
        mock_page.close = AsyncMock()
        context.new_page = AsyncMock(return_value=mock_page)

        urls = await parser.search_cards(context)

        assert len(urls) == 2

    @pytest.mark.asyncio
    async def test_get_card_details(self):
        parser = SuperJobParser(
            base_url="https://russia.superjob.ru/vacancy/search",
            host="russia.superjob.ru",
            query="Python",
            parallel=4,
            card_parse_limit=10,
        )

        details = {
            "title": "Python Backend Developer",
            "employer": "Mail.ru",
            "salary": "120000-180000 руб.",
            "description": "Ищем backend разработчика на Python",
        }

        context = AsyncMock()
        mock_page = make_mock_page_with_details(details)
        mock_page.inner_text = AsyncMock(return_value="Опыт работы от 3 лет")
        context.new_page = AsyncMock(return_value=mock_page)

        vacancy = await parser._get_card_details(context, "https://russia.superjob.ru/vakansii/python-dev-888888.html")

        assert vacancy is not None
        assert vacancy.title == "Python Backend Developer"
        assert vacancy.vacancy_id == "888888"


class TestZarplataParserIntegration:
    @pytest.mark.asyncio
    async def test_search_cards_with_links(self):
        parser = ZarplataParser(
            base_url="https://zarplata.ru/vacancy",
            host="zarplata.ru",
            query="Python",
            parallel=4,
            card_parse_limit=10,
        )

        cards_data = [
            {"url": "https://zarplata.ru/vacancy/111111"},
            {"url": "https://zarplata.ru/vacancy/222222"},
        ]

        context = AsyncMock()
        mock_page = make_mock_page_with_cards(cards_data)
        context.new_page = AsyncMock(return_value=mock_page)

        urls = await parser.search_cards(context)

        assert len(urls) == 2
        assert "https://zarplata.ru/vacancy/111111" in urls
        assert "https://zarplata.ru/vacancy/222222" in urls

    @pytest.mark.asyncio
    async def test_get_card_details(self):
        parser = ZarplataParser(
            base_url="https://zarplata.ru/vacancy",
            host="zarplata.ru",
            query="Python",
            parallel=4,
            card_parse_limit=10,
        )

        details = {
            "title": "Python Developer",
            "employer": "Tinkoff",
            "salary": "100000-150000 руб.",
            "experience": "1-3 года",
            "description": "Python разработчик в команду",
        }

        context = AsyncMock()
        mock_page = make_mock_page_with_details(details)
        context.new_page = AsyncMock(return_value=mock_page)

        vacancy = await parser._get_card_details(context, "https://zarplata.ru/vacancy/111111")

        assert vacancy is not None
        assert vacancy.title == "Python Developer"
        assert vacancy.vacancy_id == "111111"


class TestParserErrorHandling:
    @pytest.mark.asyncio
    async def test_search_cards_page_error(self):
        parser = HHParser(
            base_url="https://hh.ru/search/vacancy",
            host="hh.ru",
            query="Python",
        )

        context = AsyncMock()
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Network error"))
        mock_page.close = AsyncMock()
        context.new_page = AsyncMock(return_value=mock_page)

        with pytest.raises(Exception):
            await parser.search_cards(context)

    @pytest.mark.asyncio
    async def test_get_card_details_page_error(self):
        parser = HHParser(
            base_url="https://hh.ru/search/vacancy",
            host="hh.ru",
            query="Python",
        )

        context = AsyncMock()
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Timeout"))
        mock_page.close = AsyncMock()
        context.new_page = AsyncMock(return_value=mock_page)

        result = await parser._get_card_details(context, "https://hh.ru/vacancy/111111")
        assert result is None


class TestVacancyDTOSerialization:
    def test_to_json(self):
        dto = VacancyDTO(
            vacancy_id="12345",
            url="https://hh.ru/vacancy/12345",
            host="hh.ru",
            title="Python Developer",
            employer="Yandex",
            salary="100000",
            experience="1-3",
            description="Test",
        )
        json_str = dto.model_dump_json()
        assert "Python Developer" in json_str
        assert "12345" in json_str

    def test_from_dict(self):
        data = {
            "vacancy_id": "12345",
            "url": "https://hh.ru/vacancy/12345",
            "host": "hh.ru",
            "title": "Python Developer",
        }
        dto = VacancyDTO(**data)
        assert dto.vacancy_id == "12345"
        assert dto.title == "Python Developer"

    def test_optional_fields(self):
        dto = VacancyDTO(
            vacancy_id="1",
            url="https://test.com/1",
            host="test.com",
        )
        assert dto.title is None
        assert dto.employer is None
        assert dto.salary is None
        assert dto.experience is None
        assert dto.description is None


class TestParserQueryUpdate:
    def test_update_query(self):
        parser = HHParser(
            base_url="https://hh.ru/search/vacancy",
            host="hh.ru",
            query="Python",
        )
        assert parser.query == "Python"

        parser.query = "Java"
        assert parser.query == "Java"

        url = parser._build_url()
        assert "Java" in url

    def test_update_query_all_parsers(self):
        parsers = [
            HHParser(base_url="https://hh.ru/search/vacancy", host="hh.ru", query="Python"),
            HabrParser(base_url="https://career.habr.com/vacancies", host="career.habr.com", query="Python"),
            RabotaParser(base_url="https://www.rabota.ru/vacancy", host="www.rabota.ru", query="Python"),
            SuperJobParser(base_url="https://russia.superjob.ru/vacancy/search", host="russia.superjob.ru", query="Python"),
            ZarplataParser(base_url="https://zarplata.ru/vacancy", host="zarplata.ru", query="Python"),
        ]

        for parser in parsers:
            parser.query = "Golang"
            url = parser._build_url()
            assert "Golang" in url
