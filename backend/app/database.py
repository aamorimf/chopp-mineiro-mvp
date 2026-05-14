from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models import Base, SystemSettings

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
        """,
        """
        ALTER TABLE tabs
        ADD COLUMN apply_service_fee BOOLEAN DEFAULT 1
        """,
        """
        ALTER TABLE tabs
        ADD COLUMN apply_couvert BOOLEAN DEFAULT 0
        """,
        """
        ALTER TABLE tabs
        ADD COLUMN current_bill_total FLOAT
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

    session = SessionLocal()

    try:
        settings_exists = session.query(SystemSettings).first()

        if not settings_exists:
            settings = SystemSettings(
                service_fee_enabled=True,
                service_fee_percentage=10,
                couvert_enabled=False,
                couvert_price=0,
            )

            session.add(settings)
            session.commit()

    finally:
        session.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    run_manual_migrations()