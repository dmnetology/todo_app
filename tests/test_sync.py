import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_export_user_tasks_success(client, auth_headers, db_session):
    """
    Тест успешного экспорта задач пользователя.
    """
    # Создаём тестовые задачи
    from app.models.task import Task
    from app.models.task import TaskPriority
    
    task1 = Task(
        title="Test Task 1",
        description="Description 1",
        priority=TaskPriority.high,
        is_completed=False,
        estimated_minutes=60,
        actual_minutes=None,
        category_id=1,
        owner_id=1,
    )
    task2 = Task(
        title="Test Task 2",
        description="Description 2",
        priority=TaskPriority.low,
        is_completed=True,
        estimated_minutes=30,
        actual_minutes=25,
        category_id=2,
        owner_id=1,
    )
    
    db_session.add_all([task1, task2])
    db_session.commit()
    
    with patch("app.api.routes.sync.export_tasks", new_callable=AsyncMock) as mock_export:
        mock_export.return_value = "disk:/todo_tasks.json"
        
        response = client.post(
            "/sync/export",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "file": "disk:/todo_tasks.json"
        }
        mock_export.assert_called_once()
        # Проверяем, что в export_tasks переданы задачи пользователя
        args = mock_export.call_args[0][0]
        assert len(args) == 2
        assert args[0].title == "Test Task 1"
        assert args[1].title == "Test Task 2"


@pytest.mark.asyncio
async def test_export_user_tasks_empty(client, auth_headers, db_session):
    """
    Тест экспорта когда у пользователя нет задач.
    """
    with patch("app.api.routes.sync.export_tasks", new_callable=AsyncMock) as mock_export:
        mock_export.return_value = "disk:/todo_tasks.json"
        
        response = client.post(
            "/sync/export",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        mock_export.assert_called_once()
        # Должен быть вызван с пустым списком
        args = mock_export.call_args[0][0]
        assert len(args) == 0


@pytest.mark.asyncio
async def test_export_user_tasks_error(client, auth_headers, db_session):
    """
    Тест ошибки при экспорте задач.
    """
    with patch("app.api.routes.sync.export_tasks", new_callable=AsyncMock) as mock_export:
        mock_export.side_effect = Exception("Yandex Disk API error")
        
        response = client.post(
            "/sync/export",
            headers=auth_headers,
        )
        
        assert response.status_code == 500
        assert "detail" in response.json()
        mock_export.assert_called_once()


@pytest.mark.asyncio
async def test_import_user_tasks_success(client, auth_headers, db_session):
    """
    Тест успешного импорта задач.
    """
    mock_tasks_data = [
        {
            "title": "Imported Task 1",
            "description": "Imported Description 1",
            "priority": "high",
            "is_completed": False,
            "estimated_minutes": 60,
            "actual_minutes": None,
            "category_id": 1,
        },
        {
            "title": "Imported Task 2",
            "description": "Imported Description 2",
            "priority": "low",
            "is_completed": True,
            "estimated_minutes": 30,
            "actual_minutes": 25,
            "category_id": 2,
        },
    ]
    
    with patch("app.api.routes.sync.import_tasks", new_callable=AsyncMock) as mock_import:
        mock_import.return_value = mock_tasks_data
        
        response = client.get(
            "/sync/import",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["tasks"]) == 2
        assert data["tasks"][0]["title"] == "Imported Task 1"
        assert data["tasks"][1]["title"] == "Imported Task 2"
        mock_import.assert_called_once()


@pytest.mark.asyncio
async def test_import_user_tasks_empty(client, auth_headers, db_session):
    """
    Тест импорта когда нет файла на Яндекс.Диске.
    """
    with patch("app.api.routes.sync.import_tasks", new_callable=AsyncMock) as mock_import:
        mock_import.return_value = []
        
        response = client.get(
            "/sync/import",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert len(data["tasks"]) == 0
        mock_import.assert_called_once()


@pytest.mark.asyncio
async def test_import_user_tasks_replaces_existing(client, auth_headers, db_session):
    """
    Тест: импорт должен полностью заменить существующие задачи.
    """
    # Создаём существующую задачу
    from app.models.task import Task
    from app.models.task import TaskPriority
    
    existing_task = Task(
        title="Old Task",
        description="Should be deleted",
        priority=TaskPriority.medium,
        is_completed=False,
        estimated_minutes=10,
        actual_minutes=None,
        category_id=1,
        owner_id=1,
    )
    db_session.add(existing_task)
    db_session.commit()
    
    # Проверяем что задача есть
    old_count = db_session.query(Task).filter(Task.owner_id == 1).count()
    assert old_count == 1
    
    # Импортируем новые задачи
    mock_tasks_data = [
        {
            "title": "New Task",
            "description": "New Description",
            "priority": "high",
            "is_completed": False,
            "estimated_minutes": 45,
            "actual_minutes": None,
            "category_id": 2,
        },
    ]
    
    with patch("app.api.routes.sync.import_tasks", new_callable=AsyncMock) as mock_import:
        mock_import.return_value = mock_tasks_data
        
        response = client.get(
            "/sync/import",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        
        # Проверяем что старые задачи удалены, остались только новые
        new_count = db_session.query(Task).filter(Task.owner_id == 1).count()
        assert new_count == 1
        
        new_task = db_session.query(Task).filter(Task.owner_id == 1).first()
        assert new_task.title == "New Task"
        assert new_task.description == "New Description"


@pytest.mark.asyncio
async def test_import_user_tasks_error(client, auth_headers, db_session):
    """
    Тест ошибки при импорте задач.
    """
    with patch("app.api.routes.sync.import_tasks", new_callable=AsyncMock) as mock_import:
        mock_import.side_effect = Exception("Failed to download from Yandex Disk")
        
        response = client.get(
            "/sync/import",
            headers=auth_headers,
        )
        
        assert response.status_code == 500
        assert "detail" in response.json()
        mock_import.assert_called_once()


def test_export_unauthorized(client):
    """
    Тест: эндпоинт экспорта требует авторизации.
    """
    response = client.post("/sync/export")
    assert response.status_code == 403


def test_import_unauthorized(client):
    """
    Тест: эндпоинт импорта требует авторизации.
    """
    response = client.get("/sync/import")
    assert response.status_code == 403