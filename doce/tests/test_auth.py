import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from doce.database.database import Base, get_db
from doce.database.models import User
from doce.api.auth import get_password_hash
from doce.main import app

# Create a test database in memory
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the tables
Base.metadata.create_all(bind=engine)


# Dependency override
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture
def test_db():
    # Create the database tables
    Base.metadata.create_all(bind=engine)
    
    # Create a test user
    db = TestingSessionLocal()
    hashed_password = get_password_hash("testpassword")
    test_user = User(
        name="Test User",
        email="test@example.com",
        hashed_password=hashed_password,
        role="admin"
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    db.close()
    
    yield
    
    # Clean up
    Base.metadata.drop_all(bind=engine)


def test_login_success(test_db):
    response = client.post(
        "/api/auth/token",
        data={
            "username": "test@example.com",
            "password": "testpassword"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_invalid_credentials(test_db):
    response = client.post(
        "/api/auth/token",
        data={
            "username": "test@example.com",
            "password": "wrongpassword"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 401
    assert "detail" in response.json()


def test_login_user_not_found(test_db):
    response = client.post(
        "/api/auth/token",
        data={
            "username": "nonexistent@example.com",
            "password": "testpassword"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.fixture
def auth_token(test_db):
    response = client.post(
        "/api/auth/token",
        data={
            "username": "test@example.com",
            "password": "testpassword"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    return response.json()["access_token"]


def test_get_current_user(auth_token):
    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
    assert response.json()["name"] == "Test User"
    assert response.json()["role"] == "admin"


def test_get_current_user_invalid_token():
    response = client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401
    assert "detail" in response.json()


def test_get_current_user_no_token():
    response = client.get("/api/users/me")
    assert response.status_code == 401
    assert "detail" in response.json()