from collections.abc import Generator

from sqlmodel import Session, create_engine

from src.config import get_settings

settings = get_settings()

# Prefer pooled Neon URL for the app
_db_url = settings.database_url_pooled or settings.database_url
engine = create_engine(_db_url, echo=settings.debug)


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session
