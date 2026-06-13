import pytest


@pytest.mark.parametrize(
    "category_name",
    [
        "Учеба",
        "Работа",
        "Спорт",
    ],
)
def test_create_category(
    client,
    auth_headers,
    category_name,
):
    """
    Тест создания категории.

    Используется авторизованный запрос, так как категории принадлежат пользователю.

    Ожидаем, что:
    - категория будет создана;
    - сервер вернёт статус 201 Created;
    - в ответе будет имя созданной категории.
    """
    response = client.post(
        "/categories",
        headers=auth_headers,
        json={"name": category_name},
    )

    assert response.status_code == 201
    assert response.json()["name"] == category_name


def test_get_categories(client, auth_headers):
    """
    Тест получения списка категорий.

    Сценарий:
    1. Создаём категорию для авторизованного пользователя.
    2. Запрашиваем список категорий.
    3. Проверяем, что в списке есть одна категория.
    """
    client.post(
        "/categories",
        headers=auth_headers,
        json={"name": "Работа"},
    )

    response = client.get("/categories", headers=auth_headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_update_category(client, auth_headers):
    """
    Тест обновления категории.

    Сценарий:
    1. Создаём категорию.
    2. Берём её id из ответа.
    3. Отправляем PUT-запрос с новым названием.
    4. Проверяем, что категория обновилась.
    """
    created = client.post(
        "/categories",
        headers=auth_headers,
        json={"name": "Дом"},
    )

    category_id = created.json()["id"]

    response = client.put(
        f"/categories/{category_id}",
        headers=auth_headers,
        json={"name": "Домашние дела"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Домашние дела"


def test_delete_category(client, auth_headers):
    """
    Тест удаления категории.

    Сценарий:
    1. Создаём категорию.
    2. Получаем её id.
    3. Отправляем DELETE-запрос.
    4. Ожидаем статус 204 No Content.
    """
    created = client.post(
        "/categories",
        headers=auth_headers,
        json={"name": "Спорт"},
    )

    category_id = created.json()["id"]

    response = client.delete(
        f"/categories/{category_id}",
        headers=auth_headers,
    )

    assert response.status_code == 204


def test_create_duplicate_category(client, auth_headers):
    """
    Тест на запрет дублирования категорий.

    Сценарий:
    1. Создаём категорию с названием "Работа".
    2. Повторно пытаемся создать категорию с таким же названием.
    3. Ожидаем статус 409 Conflict.
    """
    payload = {"name": "Работа"}

    client.post("/categories", headers=auth_headers, json=payload)
    response = client.post("/categories", headers=auth_headers, json=payload)

    assert response.status_code == 409