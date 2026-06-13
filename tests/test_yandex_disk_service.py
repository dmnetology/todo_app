import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.services.yandex_disk_service import export_tasks, import_tasks
from app.models.task import Task
from app.models.task import TaskPriority


@pytest.fixture
def sample_tasks():
    """Создаёт тестовые задачи для экспорта."""
    task1 = Task(
        title="Test Task 1",
        description="Description 1",
        priority=TaskPriority.high,
        is_completed=False,
        estimated_minutes=60,
        actual_minutes=None,
        category_id=1,
    )
    task2 = Task(
        title="Test Task 2",
        description="Description 2",
        priority=TaskPriority.low,
        is_completed=True,
        estimated_minutes=30,
        actual_minutes=25,
        category_id=2,
    )
    return [task1, task2]


@pytest.mark.asyncio
@patch("app.services.yandex_disk_service.httpx.AsyncClient")
async def test_export_tasks_success(mock_client_class, sample_tasks):
    """Тест успешного экспорта задач на Яндекс.Диск."""
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    # DELETE
    mock_delete_response = MagicMock()
    mock_delete_response.status_code = 404
    mock_client.delete.return_value = mock_delete_response

    # GET upload URL
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json = MagicMock(return_value={"href": "https://upload-url.example.com"})
    mock_get_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_get_response

    # PUT upload
    mock_put_response = MagicMock()
    mock_put_response.status_code = 201
    mock_put_response.raise_for_status = MagicMock()
    mock_client.put.return_value = mock_put_response

    result = await export_tasks(sample_tasks)

    assert result == "disk:/todo_tasks.json"
    assert mock_client.delete.call_count == 1
    assert mock_client.get.call_count == 1
    assert mock_client.put.call_count == 1


@pytest.mark.asyncio
@patch("app.services.yandex_disk_service.httpx.AsyncClient")
async def test_export_tasks_with_retry(mock_client_class, sample_tasks):
    """Тест повторной попытки при конфликте (409)."""
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    mock_client.delete.return_value = MagicMock(status_code=404)

    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json = MagicMock(return_value={"href": "https://upload-url.example.com"})
    mock_get_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_get_response

    # PUT: первый раз 409, второй раз успех
    mock_put_response_409 = MagicMock()
    mock_put_response_409.status_code = 409

    mock_put_response_201 = MagicMock()
    mock_put_response_201.status_code = 201
    mock_put_response_201.raise_for_status = MagicMock()

    mock_client.put.side_effect = [mock_put_response_409, mock_put_response_201]

    result = await export_tasks(sample_tasks)

    assert result == "disk:/todo_tasks.json"
    assert mock_client.put.call_count == 2


@pytest.mark.asyncio
@patch("app.services.yandex_disk_service.httpx.AsyncClient")
async def test_import_tasks_success(mock_client_class):
    """Тест успешного импорта задач с Яндекс.Диска."""
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    # GET download URL
    mock_get_download_response = MagicMock()
    mock_get_download_response.status_code = 200
    mock_get_download_response.json = MagicMock(return_value={"href": "https://download-url.example.com"})
    mock_get_download_response.raise_for_status = MagicMock()

    # GET file content
    expected_data = [
        {
            "title": "Imported Task",
            "description": "Imported Description",
            "priority": "high",
            "is_completed": False,
            "estimated_minutes": 45,
            "actual_minutes": None,
            "category_id": 1,
        }
    ]
    mock_file_response = MagicMock()
    mock_file_response.text = json.dumps(expected_data)
    mock_file_response.status_code = 200
    mock_file_response.raise_for_status = MagicMock()

    # Важно: первый вызов get возвращает download URL, второй — файл
    mock_client.get.side_effect = [mock_get_download_response, mock_file_response]

    result = await import_tasks()

    assert len(result) == 1
    assert result[0]["title"] == "Imported Task"
    assert result[0]["priority"] == "high"


@pytest.mark.asyncio
@patch("app.services.yandex_disk_service.httpx.AsyncClient")
async def test_import_tasks_file_not_found(mock_client_class):
    """Тест: файл на Яндекс.Диске не найден (404)."""
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_client.get.return_value = mock_response

    result = await import_tasks()

    assert result == []


@pytest.mark.asyncio
@patch("app.services.yandex_disk_service.httpx.AsyncClient")
async def test_import_tasks_no_href(mock_client_class):
    """Тест: Яндекс.Диск не вернул href в ответе."""
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value={})
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    with pytest.raises(RuntimeError) as exc_info:
        await import_tasks()

    assert "did not return download URL" in str(exc_info.value)