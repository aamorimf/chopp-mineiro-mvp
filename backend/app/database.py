from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models import Base

DATABASE_URL = "sqlite:///./chopp-mineiro.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)


def run_manual_migrations():
    migrations = [
        """
        ALTER TABLE tabs
        ADD COLUMN payment_method TEXT
        """,
        """
        ALTER TABLE tabs
        ADD COLUMN closed_total FLOAT
        """,
        """
        ALTER TABLE tabs
        ADD COLUMN closed_at DATETIME
        """
    ]

    with engine.connect() as connection:
        for migration in migrations:
            try:
                connection.execute(text(migration))
                connection.commit()
            except Exception:
                # coluna já existe
                pass


def init_db():
    Base.metadata.create_all(bind=engine)
    run_manual_migrations()