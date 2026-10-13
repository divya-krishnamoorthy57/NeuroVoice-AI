import os
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL

logger = logging.getLogger("neurovoice.database")

Base = declarative_base()

# Configure SQLAlchemy engine with pool pre-ping to handle reconnections cleanly
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_connection():
    """Legacy helper for direct mysql-connector compatibility if required."""
    import mysql.connector
    import config
    return mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        autocommit=True
    )


def safe_migrate_users_table(conn):
    """Safely adds missing columns to existing users table without dropping data."""
    try:
        inspector = inspect(conn)
        columns = [col["name"] for col in inspector.get_columns("users")]

        if "role" not in columns:
            logger.info("Migrating: Adding 'role' column to users table")
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"))

        if "is_active" not in columns:
            logger.info("Migrating: Adding 'is_active' column to users table")
            conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"))

        conn.commit()
    except Exception as e:
        logger.warning(f"Note during users table check: {e}")


def safe_migrate_exercises_table(conn):
    """Safely adds missing columns to existing exercises table without dropping data."""
    try:
        inspector = inspect(conn)
        columns = [col["name"] for col in inspector.get_columns("exercises")]

        if "example_sentence" not in columns:
            logger.info("Migrating: Adding 'example_sentence' column to exercises table")
            conn.execute(text("ALTER TABLE exercises ADD COLUMN example_sentence TEXT NULL"))

        if "english_meaning" not in columns:
            logger.info("Migrating: Adding 'english_meaning' column to exercises table")
            conn.execute(text("ALTER TABLE exercises ADD COLUMN english_meaning TEXT NULL"))

        if "translated_sentence" not in columns:
            logger.info("Migrating: Adding 'translated_sentence' column to exercises table")
            conn.execute(text("ALTER TABLE exercises ADD COLUMN translated_sentence TEXT NULL"))

        if "language" not in columns:
            logger.info("Migrating: Adding 'language' column to exercises table")
            conn.execute(text("ALTER TABLE exercises ADD COLUMN language VARCHAR(20) NOT NULL DEFAULT 'en-US'"))

        conn.commit()
    except Exception as e:
        logger.warning(f"Note during exercises table check: {e}")


def safe_migrate_practice_tables(conn):
    """Safely adds language columns to practice_sessions and practice_responses tables."""
    try:
        inspector = inspect(conn)
        
        # Check practice_sessions
        session_cols = [col["name"] for col in inspector.get_columns("practice_sessions")]
        if "language" not in session_cols:
            logger.info("Migrating: Adding 'language' column to practice_sessions table")
            conn.execute(text("ALTER TABLE practice_sessions ADD COLUMN language VARCHAR(20) NOT NULL DEFAULT 'en-US'"))

        # Check practice_responses
        resp_cols = [col["name"] for col in inspector.get_columns("practice_responses")]
        if "language" not in resp_cols:
            logger.info("Migrating: Adding 'language' column to practice_responses table")
            conn.execute(text("ALTER TABLE practice_responses ADD COLUMN language VARCHAR(20) NOT NULL DEFAULT 'en-US'"))

        conn.commit()
    except Exception as e:
        logger.warning(f"Note during practice tables check: {e}")


def seed_initial_data(db):
    """Seeds starter categories and starter exercises if empty."""
    from models import ExerciseCategory, Exercise, User
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # 1. Check if admin user exists, or promote user #1 to admin
    admin_user = db.query(User).filter(User.role == "admin").first()
    if not admin_user:
        first_user = db.query(User).first()
        if first_user:
            first_user.role = "admin"
            db.commit()
            logger.info(f"Designated user {first_user.email} as initial administrator")
        else:
            default_admin = User(
                name="System Administrator",
                email="admin@neurovoice.ai",
                password=pwd_context.hash("AdminNeuroVoice2026!"),
                role="admin",
                is_active=True
            )
            db.add(default_admin)
            db.commit()
            logger.info("Created default administrator: admin@neurovoice.ai")

    # 2. Seed / Sync Exercise Categories and Real-life Exercises
    from seed_data import sync_seed_data
    sync_seed_data(db)


def init_db():
    """Initializes tables safely and seeds baseline content without data loss."""
    import models  # Ensure all models are registered with Base

    with engine.connect() as conn:
        safe_migrate_users_table(conn)
        safe_migrate_exercises_table(conn)
        safe_migrate_practice_tables(conn)

    # Create any missing tables (does not drop existing tables or columns)
    Base.metadata.create_all(bind=engine)

    # Seed baseline content if needed
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()
