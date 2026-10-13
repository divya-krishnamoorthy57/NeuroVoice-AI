import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import models  # Must import models so all tables are registered with Base.metadata
from database import Base, get_db, seed_initial_data
from main import app
from models import User
from auth import hash_password, create_access_token

# Use SQLite in-memory database with StaticPool to keep schema and tables across all connections
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_initial_data(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_token(client):
    res = client.post(
        "/auth/register",
        json={
            "name": "Jane Test",
            "email": "jane.test@example.com",
            "password": "Password123!",
            "daily_practice_goal": 15
        }
    )
    if res.status_code == 201:
        return res.json()["access_token"], res.json()["user"]
    login_res = client.post(
        "/auth/login",
        json={"email": "jane.test@example.com", "password": "Password123!"}
    )
    return login_res.json()["access_token"], login_res.json()["user"]


@pytest.fixture
def second_user_token(client):
    res = client.post(
        "/auth/register",
        json={
            "name": "Second User",
            "email": "second.user@example.com",
            "password": "Password123!"
        }
    )
    if res.status_code == 201:
        return res.json()["access_token"], res.json()["user"]
    login_res = client.post(
        "/auth/login",
        json={"email": "second.user@example.com", "password": "Password123!"}
    )
    return login_res.json()["access_token"], login_res.json()["user"]


@pytest.fixture
def admin_user_token(client, db_session):
    admin = db_session.query(User).filter(User.role == "admin").first()
    if not admin:
        admin = User(
            name="Admin Tester",
            email="admin.tester@example.com",
            password=hash_password("AdminPass123!"),
            role="admin",
            is_active=True
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)

    return create_access_token({"sub": str(admin.id), "user_id": admin.id, "email": admin.email})
