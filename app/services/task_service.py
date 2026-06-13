from datetime import datetime, UTC

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskStatusUpdate
from app.services.ai_service import predict_task_duration


def validate_category_owner(
    db: Session,
    category_id: int | None,
    user_id: int,
) -> None:
    """
    Проверяет, что указанная категория принадлежит текущему пользователю.

    Это нужно для защиты от ситуации, когда пользователь пытается
    привязать задачу к чужой категории.

    Если category_id равен None, проверка не выполняется.
    """
    if category_id is None:
        return

    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == user_id,
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )


async def create_task(db: Session, data: TaskCreate, user: User) -> Task:
    """
    Создаёт новую задачу для пользователя.

    Алгоритм:
    1. Проверяет, принадлежит ли категория пользователю.
    2. Определяет estimated_minutes:
       - если значение передано, использует его;
       - если нет, запрашивает прогноз у AI-сервиса.
    3. Создаёт объект Task.
    4. Сохраняет задачу в базе данных.
    """
    validate_category_owner(db, data.category_id, user.id)

    estimated_minutes = data.estimated_minutes

    if estimated_minutes is None:
        estimated_minutes, _ = await predict_task_duration(
            db=db,
            user_id=user.id,
            title=data.title,
            category_id=data.category_id,
        )

    task = Task(
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        priority=data.priority,
        due_date=data.due_date,
        estimated_minutes=estimated_minutes,
        owner_id=user.id,
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


def get_tasks(
    db: Session,
    user: User,
    skip: int = 0,
    limit: int = 20,
    is_completed: bool | None = None,
    category_id: int | None = None,
    sort_by: str | None = None,
) -> list[Task]:
    """
    Возвращает список задач пользователя.

    Поддерживаются:
    - пагинация через skip и limit;
    - фильтр по статусу выполнения;
    - фильтр по категории;
    - сортировка по приоритету, сроку или дате создания.
    """
    query = db.query(Task).filter(Task.owner_id == user.id)

    if is_completed is not None:
        query = query.filter(Task.is_completed == is_completed)

    if category_id is not None:
        query = query.filter(Task.category_id == category_id)

    if sort_by == "priority":
        query = query.order_by(Task.priority.desc())
    elif sort_by == "due_date":
        query = query.order_by(Task.due_date.asc())
    else:
        query = query.order_by(Task.created_at.desc())

    return query.offset(skip).limit(limit).all()


def get_task_by_id(db: Session, task_id: int, user: User) -> Task:
    """
    Возвращает задачу по её идентификатору.

    Ищет только среди задач текущего пользователя.
    Если задача не найдена, возвращает HTTP 404.
    """
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.owner_id == user.id,
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


def update_task(
    db: Session,
    task_id: int,
    data: TaskUpdate,
    user: User,
) -> Task:
    """
    Обновляет задачу пользователя.

    Используется частичное обновление:
    - передаются только поля, которые нужно изменить;
    - остальные поля остаются без изменений.

    Если обновляется category_id, проверяется,
    принадлежит ли категория текущему пользователю.
    """
    task = get_task_by_id(db, task_id, user)

    update_data = data.model_dump(exclude_unset=True)

    if "category_id" in update_data:
        validate_category_owner(db, update_data["category_id"], user.id)

    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)

    return task


def delete_task(db: Session, task_id: int, user: User) -> None:
    """
    Удаляет задачу пользователя.

    Сначала задача ищется только в рамках задач текущего пользователя,
    затем удаляется из базы.
    """
    task = get_task_by_id(db, task_id, user)

    db.delete(task)
    db.commit()


def update_task_status(
    db: Session,
    task_id: int,
    data: TaskStatusUpdate,
    user: User,
) -> Task:
    """
    Изменяет статус выполнения задачи.

    Если задача отмечается выполненной:
    - устанавливается completed_at;
    - при наличии значения actual_minutes оно сохраняется.

    Если задача помечается невыполненной:
    - completed_at сбрасывается;
    - actual_minutes очищается.
    """
    task = get_task_by_id(db, task_id, user)

    task.is_completed = data.is_completed

    if data.is_completed:
        task.completed_at = datetime.now(UTC)
        if data.actual_minutes is not None:
            task.actual_minutes = data.actual_minutes
    else:
        task.completed_at = None
        task.actual_minutes = None

    db.commit()
    db.refresh(task)

    return task