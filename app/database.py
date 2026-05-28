import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# SQLite keeps the project lightweight and easy to run for academic demos.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "adaptive_learning.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}")

if DATABASE_URL.startswith("sqlite:///"):
    database_path = Path(DATABASE_URL.replace("sqlite:///", "", 1))
    if not database_path.is_absolute():
        database_path = PROJECT_ROOT / database_path
        DATABASE_URL = f"sqlite:///{database_path.as_posix()}"
    database_path.parent.mkdir(parents=True, exist_ok=True)


# check_same_thread=False allows FastAPI request handlers to share SQLite sessions safely.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Provide a database session for each API request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create database tables automatically when the application starts."""
    from app import models

    Base.metadata.create_all(bind=engine)
    _add_missing_columns_for_lightweight_sqlite_migrations()


def _add_missing_columns_for_lightweight_sqlite_migrations():
    """Add new SQLite columns without introducing Alembic for this mini project."""
    question_columns = {
        "course": "VARCHAR DEFAULT 'Python' NOT NULL",
        "difficulty_label": "VARCHAR DEFAULT 'easy' NOT NULL",
        "question_type": "VARCHAR DEFAULT 'mcq' NOT NULL",
        "options": "TEXT",
        "correct_answer": "VARCHAR",
        "explanation": "TEXT",
        "starter_code": "TEXT",
        "test_code": "TEXT",
    }
    response_columns = {
        "session_id": "INTEGER",
        "submitted_answer": "TEXT",
    }
    student_columns = {
        "password_hash": "VARCHAR",
    }

    with engine.begin() as connection:
        _ensure_columns(connection, "students", student_columns)
        _ensure_columns(connection, "questions", question_columns)
        _ensure_columns(connection, "responses", response_columns)


def _ensure_columns(connection, table_name: str, columns: dict[str, str]):
    existing_columns = {
        row[1] for row in connection.exec_driver_sql(f"PRAGMA table_info({table_name})")
    }
    for column_name, column_type in columns.items():
        if column_name not in existing_columns:
            connection.exec_driver_sql(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )
