from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.schema import VacancyDTO
from infra.database.models import JobSearchWebSite




class BaseVacancyRepository:

    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory

    async def save_many(self, aggregated: dict[str, list[VacancyDTO]]):

        async with self.session_factory() as session:

            providers = await self._load_providers(session)

            now = datetime.now(UTC)

            rows = []

            for host, vacancies in aggregated.items():
                provider = providers[host]
                
                for v in vacancies:
                    rows.append(
                        self._build_row(v, provider.id, now)
                    )

            await self._bulk_insert(session, rows)

            await session.commit()

    async def _load_providers(self, session):
        result = await session.execute(select(JobSearchWebSite))

        return {
            p.host: p
            for p in result.scalars().all()
        }

    def _build_row(self, vacancy, provider_id, now):
        return {
            "vacancy_id": vacancy.vacancy_id,
            "url": vacancy.url,
            "title": vacancy.title,
            "employer": vacancy.employer,
            "salary": vacancy.salary,
            "experience": vacancy.experience,
            "description": vacancy.description,
            "vacancy_provider_id": provider_id,
            "created_at": now,
            "updated_at": now,
        }

    async def get_by_filter(
        self, vacancy_id: str | None = None, created_at: datetime | None = None
    ):
        async with self.session_factory() as session:
            from infra.database.models import Vacancy

            query = select(Vacancy)

            if vacancy_id:
                query = query.where(Vacancy.vacancy_id == vacancy_id)

            if created_at:
                query = query.where(Vacancy.created_at >= created_at)

            result = await session.execute(query)
            return result.scalars().all()

    async def _bulk_insert(self, session, rows):
        raise NotImplementedError


