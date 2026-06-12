from sqlalchemy.orm import Session
from rapidfuzz import fuzz
from openai import OpenAI

from app.models.task import Task
from app.core.config import settings


client = OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


def heuristic_prediction(
    db: Session,
    user_id: int,
    title: str,
    category_id: int,
) -> int:
    """
    Прогнозирует время выполнения задачи.

    Логика:
    1. Сначала ищем задачи с точным совпадением названия и категории.
    2. Если точных совпадений нет — ищем похожие названия в той же категории.
    3. Если совпадений по названию нет — используем статистику по категории.
    4. Если данных по категории нет — используем общую статистику пользователя.
    5. Если данных нет вообще — возвращаем 60.
    """

    normalized_title = " ".join(title.strip().lower().split())

    base_query = db.query(Task).filter(
        Task.owner_id == user_id,
        Task.is_completed.is_(True),
        Task.actual_minutes.isnot(None),
    )

    tasks = base_query.all()

    if not tasks:
        return 60

    # 1. Точное совпадение по названию и категории
    exact_tasks = [
        task for task in tasks
        if task.category_id == category_id
        and " ".join(task.title.strip().lower().split()) == normalized_title
    ]

    if exact_tasks:
        total = sum(task.actual_minutes for task in exact_tasks)
        return round(total / len(exact_tasks))

    # 2. Похожие названия в той же категории
    similar_tasks = [
        task for task in tasks
        if task.category_id == category_id
        and fuzz.ratio(" ".join(task.title.strip().lower().split()), normalized_title) >= 85
    ]

    if similar_tasks:
        total = sum(task.actual_minutes for task in similar_tasks)
        return round(total / len(similar_tasks))

    # 3. Статистика по категории
    category_tasks = [
        task for task in tasks
        if task.category_id == category_id
    ]

    if category_tasks:
        total = sum(task.actual_minutes for task in category_tasks)
        return round(total / len(category_tasks))

    # 4. Общая статистика пользователя
    total = sum(task.actual_minutes for task in tasks)
    return round(total / len(tasks))


async def llm_prediction(
    db: Session,
    user_id: int,
    title: str,
    category_id: int,
) -> int:
    """
    Прогнозирует время выполнения задачи через DeepSeek.
    """

    base_query = db.query(Task).filter(
        Task.owner_id == user_id,
        Task.is_completed.is_(True),
        Task.actual_minutes.isnot(None),
    ).order_by(Task.id.desc()).limit(10)

    tasks = base_query.all()

    history = "\n".join(
        f"{task.title} (cat:{task.category_id}) -> {task.actual_minutes} minutes"
        for task in tasks
    )

    prompt = f"""You are a task estimation assistant.

User completed tasks:

{history}

New task:
Title: {title}
Category ID: {category_id}

Return only integer number of minutes.

Example:
45"""

    response = client.chat.completions.create(
        model="deepseek/deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        timeout=30
    )

    result = response.choices[0].message.content.strip()
    numbers = re.findall(r"\d+", result)

    return int(numbers[0]) if numbers else 60


async def predict_task_duration(
    db: Session,
    user_id: int,
    title: str,
    category_id: int,
):
    """
    Сначала используем AI-сервис.
    При ошибке используем локальный алгоритм.
    """

    try:
        predicted_minutes = await llm_prediction(
            db=db,
            user_id=user_id,
            title=title,
            category_id=category_id,
        )

        return predicted_minutes, "llm"

    except Exception:
        return heuristic_prediction(
            db=db,
            user_id=user_id,
            title=title,
            category_id=category_id,
        ), "heuristic"