import pytest
from unittest.mock import AsyncMock
from urllib.parse import urlparse, parse_qs

from core.schema import VacancyDTO
from domain.hh import HHParser
from domain.habr import HabrParser
from domain.rabota import RabotaParser
from domain.superjob import SuperJobParser
from domain.zarplata import ZarplataParser


@pytest.fixture
def parsers():
    return {
        "hh": HHParser(
            base_url="https://hh.ru/search/vacancy",
            host="hh.ru",
            query="Python",
            parallel=4,
            card_parse_limit=10,
        ),
        "habr": HabrParser(
            base_url="https://career.habr.com/vacancies",
            host="career.habr.com",
            query="Python",
            parallel=4,
            card_parse_limit=10,
        ),
        "rabota": RabotaParser(
            base_url="https://www.rabota.ru/vacancy",
            host="www.rabota.ru",
            query="Python",
            parallel=4,
            card_parse_limit=10,
        ),
        "superjob": SuperJobParser(
            base_url="https://russia.superjob.ru/vacancy/search",
            host="russia.superjob.ru",
            query="Python",
            parallel=4,
            card_parse_limit=10,
        ),
        "zarplata": ZarplataParser(
            base_url="https://zarplata.ru/vacancy",
            host="zarplata.ru",
            query="Python",
            parallel=4,
            card_parse_limit=10,
        ),
    }


class TestVacancyDTO:
    def test_create_vacancy_dto(self):
        dto = VacancyDTO(
            vacancy_id="12345",
            url="https://hh.ru/vacancy/12345",
            host="hh.ru",
            title="Python Developer",
            employer="Yandex",
            salary="100000-150000",
            experience="1-3",
            description="Test description",
        )
        assert dto.vacancy_id == "12345"
        assert dto.title == "Python Developer"
        assert dto.employer == "Yandex"
        assert dto.salary == "100000-150000"

    def test_normalize_text_whitespace(self):
        dto = VacancyDTO(
            vacancy_id="1",
            url="https://test.com/1",
            host="test.com",
            title="  Multiple   spaces  ",
        )
        assert dto.title == "Multiple spaces"

    def test_normalize_text_none(self):
        dto = VacancyDTO(
            vacancy_id="1",
            url="https://test.com/1",
            host="test.com",
            title=None,
        )
        assert dto.title is None

    def test_normalize_all_fields(self):
        dto = VacancyDTO(
            vacancy_id="1",
            url="https://test.com/1",
            host="test.com",
            title="  Title  ",
            employer="  Employer  ",
            salary="  Salary  ",
            experience="  Exp  ",
            description="  Desc  ",
        )
        assert dto.title == "Title"
        assert dto.employer == "Employer"
        assert dto.salary == "Salary"
        assert dto.experience == "Exp"
        assert dto.description == "Desc"


class TestHHParser:
    def test_build_url(self, parsers):
        url = parsers["hh"]._build_url()
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "hh.ru"
        assert parsed.path == "/search/vacancy"
        params = parse_qs(parsed.query)
        assert params["text"] == ["Python"]

    def test_get_card_id_from_url(self, parsers):
        url = "https://hh.ru/vacancy/12345"
        assert parsers["hh"]._get_card_id_from_url(url) == "12345"

    def test_get_card_id_from_url_with_params(self, parsers):
        url = "https://hh.ru/vacancy/12345?from=direct"
        assert parsers["hh"]._get_card_id_from_url(url) == "12345"

    def test_base_query(self, parsers):
        query = parsers["hh"]._base_query()
        assert "search_field" in query
        assert "enable_snippets" in query
        assert isinstance(query["search_field"], list)


class TestHabrParser:
    def test_build_url(self, parsers):
        url = parsers["habr"]._build_url()
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "career.habr.com"
        assert parsed.path == "/vacancies"
        params = parse_qs(parsed.query)
        assert params["q"] == ["Python"]

    def test_get_card_id_from_url(self, parsers):
        url = "https://career.habr.com/vacancies/12345"
        assert parsers["habr"]._get_card_id_from_url(url) == "12345"

    def test_get_card_id_from_url_with_params(self, parsers):
        url = "https://career.habr.com/vacancies/12345?type=all"
        assert parsers["habr"]._get_card_id_from_url(url) == "12345"

    def test_base_query(self, parsers):
        query = parsers["habr"]._base_query()
        assert "q" in query
        assert "sort" in query
        assert "type" in query


class TestRabotaParser:
    def test_build_url(self, parsers):
        url = parsers["rabota"]._build_url()
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "www.rabota.ru"
        assert parsed.path == "/vacancy"
        params = parse_qs(parsed.query)
        assert params["query"] == ["Python"]

    def test_get_card_id_from_url(self, parsers):
        url = "https://www.rabota.ru/vacancy/123456"
        assert parsers["rabota"]._get_card_id_from_url(url) == "123456"

    def test_get_card_id_from_url_with_params(self, parsers):
        url = "https://www.rabota.ru/vacancy/123456?from=direct"
        assert parsers["rabota"]._get_card_id_from_url(url) == "123456"

    def test_base_query(self, parsers):
        query = parsers["rabota"]._base_query()
        assert "query" in query
        assert "location.kind" in query
        assert "location.name" in query


class TestSuperJobParser:
    def test_build_url(self, parsers):
        url = parsers["superjob"]._build_url()
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "russia.superjob.ru"
        params = parse_qs(parsed.query)
        assert params["keywords"] == ["Python"]

    def test_get_card_id_from_url(self, parsers):
        url = "https://russia.superjob.ru/vakansii/12345.html"
        assert parsers["superjob"]._get_card_id_from_url(url) == "12345"

    def test_get_card_id_from_url_complex(self, parsers):
        url = "https://russia.superjob.ru/vakansii/python-razrabotchik-12345.html?geo"
        result = parsers["superjob"]._get_card_id_from_url(url)
        assert result == "12345"

    def test_base_query(self, parsers):
        query = parsers["superjob"]._base_query()
        assert "keywords" in query
        assert "noGeo" in query


class TestZarplataParser:
    def test_build_url(self, parsers):
        url = parsers["zarplata"]._build_url()
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "zarplata.ru"
        assert parsed.path == "/vacancy"
        params = parse_qs(parsed.query)
        assert params["text"] == ["Python"]

    def test_get_card_id_from_url(self, parsers):
        url = "https://zarplata.ru/vacancy/12345"
        assert parsers["zarplata"]._get_card_id_from_url(url) == "12345"

    def test_get_card_id_from_url_with_trailing_slash(self, parsers):
        url = "https://zarplata.ru/vacancy/12345/"
        assert parsers["zarplata"]._get_card_id_from_url(url) == "12345"

    def test_get_card_id_from_url_with_params(self, parsers):
        url = "https://zarplata.ru/vacancy/12345?from=search"
        assert parsers["zarplata"]._get_card_id_from_url(url) == "12345"

    def test_base_query(self, parsers):
        query = parsers["zarplata"]._base_query()
        assert "text" in query


class TestAllParsersIntegration:
    @pytest.mark.asyncio
    async def test_search_cards_returns_urls(self, parsers):
        for name, parser in parsers.items():
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)

            mock_page.goto = AsyncMock()
            mock_page.wait_for_selector = AsyncMock()
            mock_page.query_selector_all = AsyncMock(return_value=[])
            mock_page.close = AsyncMock()

            result = await parser.search_cards(mock_context)
            assert isinstance(result, list), f"{name}: search_cards should return list"

    @pytest.mark.asyncio
    async def test_parse_cards_empty_urls(self, parsers):
        for name, parser in parsers.items():
            mock_context = AsyncMock()
            result = await parser.parse_cards(mock_context, [])
            assert result == [], f"{name}: parse_cards with empty urls should return empty list"

    def test_logger_info(self, parsers):
        for name, parser in parsers.items():
            info = parser.logger_info()
            assert "parser" in info
            assert "host" in info
            assert "url" in info
            assert "parallel" in info
            assert "card_parse_limit" in info
            assert info["parser"] == parser.__class__.__name__


class TestVacancyDTOEdgeCases:
    def test_empty_strings(self):
        dto = VacancyDTO(
            vacancy_id="1",
            url="https://test.com/1",
            host="test.com",
            title="",
            employer="",
        )
        assert dto.title == ""
        assert dto.employer == ""

    def test_unicode_text(self):
        dto = VacancyDTO(
            vacancy_id="1",
            url="https://test.com/1",
            host="test.com",
            title="Python-разработчик",
        )
        assert dto.title == "Python-разработчик"

    def test_long_description(self):
        long_desc = "A" * 10000
        dto = VacancyDTO(
            vacancy_id="1",
            url="https://test.com/1",
            host="test.com",
            description=long_desc,
        )
        assert len(dto.description) == 10000

    def test_special_characters(self):
        dto = VacancyDTO(
            vacancy_id="1",
            url="https://test.com/1",
            host="test.com",
            title="Python/Django & Flask <REST API>",
        )
        assert dto.title == "Python/Django & Flask <REST API>"


class TestParserUrlBuilders:
    def test_hh_url_encoding(self, parsers):
        parsers["hh"].query = "C++ developer"
        url = parsers["hh"]._build_url()
        assert "C%2B%2B" in url or "C++" in url

    def test_habr_url_encoding(self, parsers):
        parsers["habr"].query = "C++ developer"
        url = parsers["habr"]._build_url()
        assert "C%2B%2B" in url or "C++" in url

    def test_rabota_url_encoding(self, parsers):
        parsers["rabota"].query = "C++ developer"
        url = parsers["rabota"]._build_url()
        assert "C%2B%2B" in url or "C++" in url

    def test_superjob_url_encoding(self, parsers):
        parsers["superjob"].query = "C++ developer"
        url = parsers["superjob"]._build_url()
        assert "C%2B%2B" in url or "C++" in url

    def test_zarplata_url_encoding(self, parsers):
        parsers["zarplata"].query = "C++ developer"
        url = parsers["zarplata"]._build_url()
        assert "C%2B%2B" in url or "C++" in url


class TestParserCardIdExtraction:
    def test_hh_various_urls(self, parsers):
        assert parsers["hh"]._get_card_id_from_url("https://hh.ru/vacancy/111") == "111"
        assert parsers["hh"]._get_card_id_from_url("https://hh.ru/vacancy/222?text=python") == "222"
        assert parsers["hh"]._get_card_id_from_url("https://hh.ru/vacancy/333?from=direct") == "333"

    def test_habr_various_urls(self, parsers):
        assert parsers["habr"]._get_card_id_from_url("https://career.habr.com/vacancies/111") == "111"
        assert parsers["habr"]._get_card_id_from_url("https://career.habr.com/vacancies/222?type=all") == "222"

    def test_rabota_various_urls(self, parsers):
        assert parsers["rabota"]._get_card_id_from_url("https://www.rabota.ru/vacancy/111") == "111"
        assert parsers["rabota"]._get_card_id_from_url("https://www.rabota.ru/vacancy/222?from=direct") == "222"

    def test_superjob_various_urls(self, parsers):
        assert parsers["superjob"]._get_card_id_from_url("https://russia.superjob.ru/vakansii/111.html") == "111"
        assert parsers["superjob"]._get_card_id_from_url("https://russia.superjob.ru/vakansii/222.html?geo") == "222"
        assert parsers["superjob"]._get_card_id_from_url("https://russia.superjob.ru/vakansii/developer-333.html") == "333"

    def test_zarplata_various_urls(self, parsers):
        assert parsers["zarplata"]._get_card_id_from_url("https://zarplata.ru/vacancy/111") == "111"
        assert parsers["zarplata"]._get_card_id_from_url("https://zarplata.ru/vacancy/222/") == "222"
        assert parsers["zarplata"]._get_card_id_from_url("https://zarplata.ru/vacancy/333?from=search") == "333"
