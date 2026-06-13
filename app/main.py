from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.categories import router as categories_router
from app.api.routes.tasks import router as tasks_router
from app.core.config import settings

from app.api.routes.sync import router as sync_router

from fastapi.middleware.cors import CORSMiddleware

# Создаём экземпляр FastAPI-приложения.
#
# Здесь задаются основные метаданные приложения:
# - title: название API, которое будет видно в Swagger UI;
# - description: краткое описание проекта;
# - version: версия API.
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API для приложения: Управление задачами (To-Do App)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """
    Проверяет работоспособность приложения.

    Это простой технический эндпоинт, который можно использовать:
    - для проверки, что сервис запущен;
    - для health-check в Docker/Kubernetes;
    - для мониторинга доступности API.

    Если приложение работает корректно, возвращается статус ok.
    """
    return {"status": "ok"}

# Подключаем роутеры всех основных разделов API.
#
# Каждый роутер отвечает за отдельную область подзадач:
# - auth_router - аутентификация и регистрация;
# - categories_router - категории задач;
# - tasks_router - задачи и прогноз времени.
# - sync_router - синхронизация с внешним хранилищем 

app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(tasks_router)
app.include_router(sync_router)