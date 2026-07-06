from pydantic import BaseModel, field_validator


class VacancyDTO(BaseModel):
    vacancy_id: str
    url: str

    title: str | None = None
    employer: str | None = None
    salary: str | None = None
    experience: str | None = None
    description: str | None = None

    @field_validator(
        "title",
        "employer",
        "salary",
        "experience",
        "description",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: str | None):
        if value is None:
            return None

        value = " ".join(value.split())

        return value.strip()