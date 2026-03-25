from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def _build_engine():
    connect_args = {}
    if settings.MYSQL_UNIX_SOCKET and settings.DATABASE_URL.startswith("mysql"):
        connect_args["unix_socket"] = settings.MYSQL_UNIX_SOCKET
    if settings.DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine_kwargs = {"pool_pre_ping": True}
    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    return create_engine(settings.DATABASE_URL, **engine_kwargs)


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def rebuild_engine():
    global engine
    engine.dispose()
    engine = _build_engine()
    SessionLocal.configure(bind=engine)
    return engine


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
