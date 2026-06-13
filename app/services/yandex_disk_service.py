import json
import httpx

from app.models.task import Task
from app.core.config import settings
import asyncio

YANDEX_DISK_API = "https://cloud-api.yandex.net/v1/disk/resources"
FILE_PATH = "disk:/todo_tasks.json"


async def export_tasks(tasks):
    data = [
        {
            "title": t.title,
            "description": t.description,
            "priority": t.priority.value,
            "is_completed": t.is_completed,
            "estimated_minutes": t.estimated_minutes,
            "actual_minutes": t.actual_minutes,
            "category_id": t.category_id,
        }
        for t in tasks
    ]

    async with httpx.AsyncClient(timeout=30) as client:

        # 1. удаляем старый файл (игнорируем 404)
        await client.delete(
            YANDEX_DISK_API,
            headers={"Authorization": f"OAuth {settings.YANDEX_DISK_TOKEN}"},
            params={"path": FILE_PATH},
        )

        # 2. получаем upload url
        resp = await client.get(
            f"{YANDEX_DISK_API}/upload",
            headers={"Authorization": f"OAuth {settings.YANDEX_DISK_TOKEN}"},
            params={"path": FILE_PATH, "overwrite": "true"},
        )
        resp.raise_for_status()

        upload_url = resp.json().get("href")
        if not upload_url:
            raise RuntimeError(resp.text)

        # 3. upload (с retry на 409)
        for attempt in range(3):
            r = await client.put(
                upload_url,
                content=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            )

            if r.status_code == 409:
                await asyncio.sleep(0.5)
                continue

            r.raise_for_status()
            break

    return FILE_PATH


async def import_tasks() -> list[dict]:
    """
    Загружает задачи с Яндекс.Диска.
    """

    async with httpx.AsyncClient() as client:
        # 1. Получаем download URL
        response = await client.get(
            f"{YANDEX_DISK_API}/download",
            headers={
                "Authorization": f"OAuth {settings.YANDEX_DISK_TOKEN}",
            },
            params={
                "path": FILE_PATH,
            },
        )

        # если файла нет — не падаем с 500
        if response.status_code == 404:
            return []

        response.raise_for_status()

        download_url = response.json().get("href")
        if not download_url:
            raise RuntimeError(f"Yandex Disk did not return download URL: {response.text}")

        # 2. Загружаем содержимое файла
        file_response = await client.get(download_url, follow_redirects=True)
        file_response.raise_for_status()

    return json.loads(file_response.text)