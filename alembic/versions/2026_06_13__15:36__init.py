"""init

Revision ID: a38fce1e6c72
Revises:
Create Date: 2026-06-13 15:36:32.455247
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a38fce1e6c72"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        "job_search_web_site",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("host", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_search_web_site")),
        sa.UniqueConstraint("host", name=op.f("uq_job_search_web_site_host")),
    )

    op.create_table(
        "vacancies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vacancy_id", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("employer", sa.String(), nullable=True),
        sa.Column("salary", sa.String(), nullable=True),
        sa.Column("experience", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vacancy_provider_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["vacancy_provider_id"],
            ["job_search_web_site.id"],
            name=op.f("fk_vacancies_job_search_web_site_id"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vacancies")),
        sa.UniqueConstraint("vacancy_id", name=op.f("uq_vacancies_vacancy_id")),
    )

    op.create_index(
        op.f("ix_vacancies_vacancy_provider_id"),
        "vacancies",
        ["vacancy_provider_id"],
        unique=False,
    )

    providers = [
        "hh.ru",
        "career.habr.com",
        "www.rabota.ru",
        "russia.superjob.ru",
        "zarplata.ru",
    ]

    values = ",".join(f"('{p}')" for p in providers)

    op.execute(
        f"""
        INSERT INTO job_search_web_site (host)
        VALUES {values}
        ON CONFLICT (host) DO NOTHING
        """
    )


def downgrade() -> None:

    op.drop_index(op.f("ix_vacancies_vacancy_provider_id"), table_name="vacancies")
    op.drop_table("vacancies")
    op.drop_table("job_search_web_site")