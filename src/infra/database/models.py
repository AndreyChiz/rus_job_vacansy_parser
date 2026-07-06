from typing import (
    Annotated,
    Optional,
)

from sqlalchemy import (
    DateTime,
    ForeignKey,
    MetaData,
    event,
    func,
)

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

from datetime import datetime

TIME_NOW = Annotated[ # TODO delete
    DateTime,
    mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
]


class CustomDeclarativeBase(
    DeclarativeBase,
):
    __abstract__ = True

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )

    def __repr__(self) -> str:
        values = ", ".join(
            f"{key}={value!r}"
            for key, value in self.__dict__.items()
            if not key.startswith("_")
        )
        return f"{self.__class__.__name__}({values})"


# @event.listens_for(CustomDeclarativeBase, "before_update")
# def receive_before_update(mapper, connection, target):
#     print(f"Updating {target.__tablename__}: {target}")  # TODO refactopr via logger


# @event.listens_for(CustomDeclarativeBase, "before_insert")
# def receive_before_insert(mapper, connection, target):
#     print(
#         f"Inserting into {target.__tablename__}: {target}"
#     )  # TODO refactopr via logger


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class JobSearchWebSite(CustomDeclarativeBase):
    __tablename__ = "job_search_web_site"

    id: Mapped[int] = mapped_column(primary_key=True)
    host: Mapped[str] = mapped_column(unique=True, nullable=False)

    vacancies: Mapped[list["Vacancy"]] = relationship(
        back_populates="vacancy_provider",
        lazy="selectin",
    )


class Vacancy(CustomDeclarativeBase, TimestampMixin):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True)

    vacancy_id: Mapped[str] = mapped_column(unique=True, nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)

    title: Mapped[Optional[str]]
    employer: Mapped[Optional[str]]
    salary: Mapped[Optional[str]]
    experience: Mapped[Optional[str]]
    description: Mapped[Optional[str]]

    vacancy_provider_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(
            "job_search_web_site.id",   # FIXED HERE
            ondelete="SET NULL",
        ),
        index=True,
    )

    vacancy_provider: Mapped[Optional["JobSearchWebSite"]] = relationship(
        back_populates="vacancies",
        lazy="joined",
    )