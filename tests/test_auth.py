import pytest


@pytest.mark.parametrize(
    "first_name,last_name,login,password",
    [
        ("Petr", "Petrov", "petr@example.com", "Pass_word123!"),
        ("Anna", "Smirnova", "anna@example.com", "Pass_word456!"),
    ],
)
def test_register_user(
    client,
    first_name,
    last_name,
    login,
    password,
):
    """
    Тест регистрации пользователя.

    Ожидаем, что:
    - запрос завершится успешно;
    - сервер вернёт статус 201 Created;
    - в ответе будет логин созданного пользователя.
    """
    response = client.post(
        "/auth/register",
        json={
            "first_name": first_name,
            "last_name": last_name,
            "login": login,
            "password": password,
        },
    )

    assert response.status_code == 201
    assert response.json()["login"] == login


def test_register_duplicate_login(client):
    """
    Тест на уникальность логина.

    Сценарий:
    1. Регистрируем первого пользователя.
    2. Пытаемся зарегистрировать второго с тем же login.
    3. Ожидаем ошибку 409 Conflict.
    """
    payload = {
        "first_name": "Petr",
        "last_name": "Petrov",
        "login": "petr@example.com",
        "password": "Pass_word123!",
    }

    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)

    assert response.status_code == 409


@pytest.mark.parametrize(
    "password,expected_status",
    [
        ("Pass_word123!", 200),
        ("wrong_password", 401),
    ],
)
def test_login(
    client,
    password,
    expected_status,
):
    """
    Тест авторизации пользователя.

    Сценарии:
    - успешный вход;
    - вход с неправильным паролем.
    """
    client.post(
        "/auth/register",
        json={
            "first_name": "Anna",
            "last_name": "Smirnova",
            "login": "anna@example.com",
            "password": "Pass_word123!",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "login": "anna@example.com",
            "password": password,
        },
    )

    assert response.status_code == expected_status

    if expected_status == 200:
        assert "access_token" in response.json()


def test_change_password(client, auth_headers):
    """
    Тест смены пароля.

    Используется готовый заголовок авторизации из фикстуры auth_headers.
    Ожидаем, что:
    - запрос выполнится успешно;
    - сервер вернёт статус 204 No Content;
    - пароль пользователя будет обновлён.
    """
    response = client.post(
        "/auth/change-password",
        headers=auth_headers,
        json={
            "old_password": "Password123!",
            "new_password": "New_password123!",
        },
    )

    assert response.status_code == 204


def test_refresh_token(client):
    """
    Тест обновления токена.

    Сценарий:
    1. Регистрируем пользователя.
    2. Логинимся и получаем refresh_token.
    3. Отправляем refresh_token на endpoint /auth/refresh.
    4. Проверяем, что сервер возвращает новый access_token.
    """
    client.post(
        "/auth/register",
        json={
            "first_name": "Olga",
            "last_name": "Sokolova",
            "login": "olga@example.com",
            "password": "Pass_word123!",
        },
    )

    login_response = client.post(
        "/auth/login",
        json={
            "login": "olga@example.com",
            "password": "Pass_word123!",
        },
    )

    refresh_token = login_response.json()["refresh_token"]

    response = client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()