import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import app


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# Создаём SQLAlchemy engine для тестовой базы.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Фабрика тестовых сессий SQLAlchemy.
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture()
def db_session():
    """
    Создаёт чистую тестовую базу данных для каждого теста.

    Что происходит:
    - удаляются все таблицы;
    - создаются таблицы заново;
    - открывается новая сессия SQLAlchemy;
    - после теста сессия закрывается.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session):
    """
    Создаёт тестовый клиент FastAPI.

    Эта фикстура подменяет зависимость get_db,
    чтобы все запросы в тестах использовали тестовую SQLite-базу,
    а не реальную рабочую БД приложения.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """
    Регистрирует тестового пользователя и возвращает заголовки авторизации.

    Последовательность действий:
    1. Регистрируем пользователя через /auth/register.
    2. Логинимся через /auth/login.
    3. Извлекаем access_token из ответа.
    4. Возвращаем заголовок Authorization для дальнейших запросов.
    """
    client.post(
        "/auth/register",
        json={
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "login": "ivan@example.com",
            "password": "Password123!",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "login": "ivan@example.com",
            "password": "Password123!", 
        },
    )

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }