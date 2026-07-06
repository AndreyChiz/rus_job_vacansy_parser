from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.base.base_vacancy_reposytory import BaseVacancyRepository
from core.base.base_database import BaseDatabaseProvider
from infra.database.models import Vacancy


class SQLiteVacancyRepository(BaseVacancyRepository):

    async def _bulk_insert(self, session, rows):
        if not rows:
            return

        stmt = sqlite_insert(Vacancy).values(rows)

        stmt = stmt.on_conflict_do_nothing(
            index_elements=["vacancy_id"]
        )

        await session.execute(stmt)


class PostgresVacancyRepository(BaseVacancyRepository):

    async def _bulk_insert(self, session, rows):
        if not rows:
            return

        stmt = pg_insert(Vacancy).values(rows)

        stmt = stmt.on_conflict_do_nothing(
            index_elements=["vacancy_id"]
        )

        await session.execute(stmt)


def vacancy_repository_factory(
    database: BaseDatabaseProvider,
) -> BaseVacancyRepository:

    if database.dialect == "postgres":
        return PostgresVacancyRepository(database.get_session_factory())

    if database.dialect == "sqlite":
        return SQLiteVacancyRepository(database.get_session_factory())

    raise ValueError(f"Unsupported database dialect: {database.dialect}")