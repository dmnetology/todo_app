from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.task import Task
from app.models.user import User
from app.services.yandex_disk_service import import_tasks, export_tasks

router = APIRouter(prefix="/sync", tags=["Sync"])


@router.post("/export")
async def export_user_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Экспортирует все задачи пользователя на Яндекс.Диск."""
    try:
        tasks = db.query(Task).filter(Task.owner_id == current_user.id).all()
        filename = await export_tasks(tasks)
        return {"status": "success", "file": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/import")
async def import_user_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Импортирует задачи с Яндекс.Диска.
    Полностью заменяет все задачи пользователя на задачи из файла.
    """
    try:
        # Получаем задачи из файла
        tasks_data = await import_tasks()
        
        # Удаляем все существующие задачи пользователя
        db.query(Task).filter(Task.owner_id == current_user.id).delete()
        
        # Создаем новые задачи из файла
        imported_tasks = []
        for task_data in tasks_data:
            task = Task(
                title=task_data["title"],
                description=task_data.get("description"),
                priority=task_data.get("priority", "medium"),
                is_completed=task_data.get("is_completed", False),
                estimated_minutes=task_data.get("estimated_minutes"),
                actual_minutes=task_data.get("actual_minutes"),
                category_id=task_data.get("category_id"),
                owner_id=current_user.id,
            )
            db.add(task)
            imported_tasks.append(task)
        
        db.commit()
        
        # Обновляем объекты для получения id
        for task in imported_tasks:
            db.refresh(task)
        
        return {
            "count": len(imported_tasks),
            "tasks": imported_tasks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))