from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.task import (
    TaskCreate,
    TaskRead,
    TaskUpdate,
    TaskStatusUpdate,
    TaskEstimateResponse,
)
from app.services.task_service import (
    create_task,
    get_tasks,
    get_task_by_id,
    update_task,
    delete_task,
    update_task_status,
)

from app.services.ai_service import predict_task_duration

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Создаёт новую задачу для текущего пользователя.

    Шаги:
    1. Получаем данные задачи из тела запроса.
    2. Определяем текущего пользователя через access-token.
    3. Используем сервисный слой для создания задачи.
    4. Возвращаем созданную задачу в формате TaskRead.
    """
    return await create_task(db, data, current_user)


@router.get("", response_model=list[TaskRead])
def read_tasks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    is_completed: bool | None = None,
    category_id: int | None = None,
    sort_by: str | None = Query(default=None, pattern="^(priority|due_date)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Возвращает список задач текущего пользователя.

    Поддерживаются:
    - пагинация через skip и limit;
    - фильтрация по статусу выполнения;
    - фильтрация по категории;
    - сортировка по priority или due_date.

    Параметры Query используются для валидации входных значений:
    - skip не может быть отрицательным;
    - limit ограничен диапазоном от 1 до 100;
    - sort_by может быть только priority или due_date.
    """
    return get_tasks(
        db=db,
        user=current_user,
        skip=skip,
        limit=limit,
        is_completed=is_completed,
        category_id=category_id,
        sort_by=sort_by,
    )

@router.get("/ai/estimate", response_model=TaskEstimateResponse)
async def estimate_task_time(
    title: str = Query(..., min_length=1),
    category_id: int = Query(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Возвращает прогноз времени выполнения задачи.

    Логика прогноза:
    - сначала ищется точное совпадение по названию и категории;
    - затем ищется похожее совпадение по названию и категории;
    - если совпадений по названию нет, используется статистика по категории;
    - если данных по категории нет, используется общая статистика пользователя;
    - если данных нет совсем, возвращается значение по умолчанию.
    """

    predicted_minutes, source = await predict_task_duration(
        db=db,
        user_id=current_user.id,
        title=title,
        category_id=category_id,
    )

    return TaskEstimateResponse(predicted_minutes=predicted_minutes, source=source)


@router.get("/{task_id}", response_model=TaskRead)
def read_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Возвращает одну задачу по её идентификатору.

    Важно:
    - ищется только задача текущего пользователя;
    - если задача не найдена, сервисный слой вернёт 404.
    """
    return get_task_by_id(db, task_id, current_user)


@router.put("/{task_id}", response_model=TaskRead)
def edit_task(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Полностью или частично обновляет задачу.

    На уровне API:
    - принимаются новые данные задачи;
    - передаются в сервисный слой;
    - возвращается обновлённая запись.

    Проверка прав доступа выполняется внутри сервисов.
    """
    return update_task(db, task_id, data, current_user)


@router.patch("/{task_id}/status", response_model=TaskRead)
def change_task_status(
    task_id: int,
    data: TaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Изменяет только статус выполнения задачи.

    Этот эндпоинт удобен для сценариев:
    - отметить задачу выполненной;
    - снять отметку выполнения;
    - сохранить фактическое время выполнения.
    """
    return update_task_status(db, task_id, data, current_user)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Удаляет задачу текущего пользователя.

    Возвращает статус 204 No Content, если удаление прошло успешно.
    """
    delete_task(db, task_id, current_user)