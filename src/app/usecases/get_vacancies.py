from typing import List, Optional
from datetime import datetime
from core.schema import VacancyDTO
from infra.database.models import Vacancy

class GetVacanciesUseCase:
    def __init__(self, repository):
        self.vacancy_repository = repository

    async def execute(self, vacancy_id: Optional[str] = None, created_at: Optional[datetime] = None) -> List[VacancyDTO]:
        vacancies = await self.vacancy_repository.get_by_filter(
            vacancy_id=vacancy_id, 
            created_at=created_at
        )
        
        return [
            VacancyDTO(
                vacancy_id=v.vacancy_id,
                url=v.url,
                title=v.title,
                employer=v.employer,
                salary=v.salary,
                experience=v.experience,
                description=v.description
            )
            for v in vacancies
        ]
