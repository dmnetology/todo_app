from datetime import datetime

from pydantic import BaseModel, Field

from app.models.task import TaskPriority


class TaskCreate(BaseModel):
    """
    Pydantic-схема для создания задачи.

    Эта схема описывает данные, которые клиент отправляет
    при добавлении новой задачи через API.

    Используется для:
    - валидации входящего JSON;
    - ограничения длины текста;
    - задания значений по умолчанию;
    - генерации OpenAPI-документации.
    """

    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    category_id: int | None = None
    priority: TaskPriority = TaskPriority.medium
    due_date: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=1)


class TaskUpdate(BaseModel):
    """
    Pydantic-схема для обновления задачи.

    Эта схема используется, когда клиент меняет данные уже существующей задачи.

    Все поля сделаны необязательными, чтобы можно было обновлять
    только часть информации.
    """

    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    category_id: int | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=1)


class TaskStatusUpdate(BaseModel):
    """
    Pydantic-схема для изменения статуса задачи.

    Обычно используется в endpoint, который помечает задачу
    выполненной или невыполненной.

    Дополнительно может передаваться фактическое время выполнения.
    """

    is_completed: bool
    actual_minutes: int | None = Field(default=None, ge=1)


class TaskRead(BaseModel):
    """
    Pydantic-схема ответа с задачей.

    Эта схема используется, когда API возвращает данные задачи клиенту.

    В ней содержатся все основные поля задачи, но только в безопасном виде,
    без внутренних ORM-деталей.
    """

    id: int
    title: str
    description: str | None
    is_completed: bool
    priority: TaskPriority
    due_date: datetime | None
    created_at: datetime
    completed_at: datetime | None
    estimated_minutes: int | None
    actual_minutes: int | None
    category_id: int | None

    model_config = {
        "from_attributes": True,
    }


class TaskEstimateResponse(BaseModel):
    """
    Pydantic-схема ответа с прогнозом времени выполнения задачи.

    Используется, например, если приложение вычисляет
    предполагаемую длительность задачи на основе её параметров,
    статистики или правил планирования.
    """

    predicted_minutes: int
    source: str