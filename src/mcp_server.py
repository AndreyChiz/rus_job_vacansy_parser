from contextlib import asynccontextmanager
from fastmcp import FastMCP
from datetime import datetime
from app.container import Container


container = Container()

@asynccontextmanager
async def lifespan(app):
    await container.lifespan.start()
    yield
    await container.lifespan.stop()

mcp = FastMCP("VacancyParser", lifespan=lifespan)

@mcp.tool()
async def get_vacancies(vacancy_id: str | None = None, created_after: str | None = None):
    """
    Retrieve vacancies from the database based on vacancy_id and/or creation date.
    :param vacancy_id: The unique identifier of the vacancy.
    :param created_after: ISO format date string (YYYY-MM-DD) to filter vacancies created after this date.
    """
    from app.usecases.get_vacancies import GetVacanciesUseCase

    created_at = None
    if created_after:
        try:
            created_at = datetime.fromisoformat(created_after)
        except ValueError:
            return f"Invalid date format: {created_after}. Please use ISO format (YYYY-MM-DD)."

    usecase = GetVacanciesUseCase(container.get_vacancy_repository())
    results = await usecase.execute(vacancy_id=vacancy_id, created_at=created_at)

    return [v.model_dump() for v in results]

@mcp.tool()
async def get_count_vacancies(created_after: str | None = None):
    """
    Return count of rows vacancies.
    :param created_after: ISO format date string (YYYY-MM-DD) to filter vacancies created after this date.
    """
    from app.usecases.get_vacancies import GetVacanciesUseCase

    created_at = None
    if created_after:
        try:
            created_at = datetime.fromisoformat(created_after)
        except ValueError:
            return f"Invalid date format: {created_after}. Please use ISO format (YYYY-MM-DD)."

    usecase = GetVacanciesUseCase(container.get_vacancy_repository())
    results = await usecase.execute(created_at=created_at)

    return len([v.model_dump() for v in results])

if __name__ == "__main__":
    mcp.run(transport="streamable-http")