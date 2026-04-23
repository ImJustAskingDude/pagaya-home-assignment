from app.celery_app import celery_app
from app.task_handlers.jobs import execute_task


class CeleryDispatcher:
    def enqueue(self, task_id: int) -> str:
        async_result = execute_task.apply_async(args=[task_id])
        return async_result.id

    def revoke(self, celery_task_id: str) -> None:
        celery_app.control.revoke(celery_task_id, terminate=False)


dispatcher = CeleryDispatcher()

