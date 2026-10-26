from collections.abc import Generator

from sqlmodel import Session, create_engine

from src.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, echo=settings.debug)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session