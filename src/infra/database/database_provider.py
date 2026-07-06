from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

from core.base.base_database import BaseDatabaseBackend, BaseDatabaseProvider, Dialect

DIALECTS = ("sqlite", "postgres")


class SQLiteBackend(BaseDatabaseBackend):
    def create_engine(self, url: str):
        return create_async_engine(
            url,
            connect_args={"check_same_thread": False},
        )


class PostgresBackend(BaseDatabaseBackend):
    def __init__(self, **engine_kwargs):
        self.engine_kwargs = engine_kwargs

    def create_engine(self, url: str):
        return create_async_engine(
            url,
            **self.engine_kwargs,
        )

class DatabaseStopped:
    pass


class DatabaseRunning:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    def get_session_factory(self):
        return self._session_factory



class DatabaseProvider(BaseDatabaseProvider):
    def __init__(self, db_type: str, url: str):
        self._db_type: str = db_type   
        self.url = url

        self.engine = None
        self.state = DatabaseStopped()

        self.backend: BaseDatabaseBackend | None = None

    # -------------------------
    # normalize config → dialect
    # -------------------------
    @property
    def dialect(self) -> Dialect:
        if self._db_type not in DIALECTS:
            raise ValueError(f"Unsupported db type: {self._db_type}")
        return self._db_type  # type: ignore

    # -------------------------
    # lifecycle
    # -------------------------
    async def start(self) -> None:
        if self._db_type == "sqlite":
            self.backend = SQLiteBackend()

        elif self._db_type == "postgres":
            self.backend = PostgresBackend(
                pool_size=5,
                max_overflow=10,
            )

        else:
            raise ValueError(f"Unsupported db type: {self._db_type}")

        self.engine = self.backend.create_engine(self.url)

        session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

        self.state = DatabaseRunning(session_factory)

    async def stop(self) -> None:
        if self.engine:
            await self.engine.dispose()

        self.engine = None
        self.state = DatabaseStopped()

    # -------------------------
    # API
    # -------------------------
    def get_session_factory(self):
        if isinstance(self.state, DatabaseStopped):
            raise RuntimeError("Database not started")

        return self.state.get_session_factory()
