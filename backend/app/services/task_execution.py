from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.core.enums import TaskStatus
from app.models.task import TaskModel
from app.repositories.tasks import TaskRepository
from app.task_handlers.cancellation import TaskCancelled
from app.task_handlers.registry import get_handler

Retry = Callable[..., Any]


class TaskExecutionService:
    def __init__(self, session: Session, retry: Retry) -> None:
        self.retry = retry
        self.tasks = TaskRepository(session)

    def execute(self, task_id: int) -> dict[str, Any]:
        task = self.tasks.get(task_id)
        if task is None:
            return {"ignored": True, "reason": "task_not_found"}
        if task.status == TaskStatus.CANCELLED.value or task.cancel_requested_at is not None:
            self.tasks.mark_cancelled(task)
            return {"cancelled": True}

        self.tasks.mark_running(task)

        try:
            handler = get_handler(task.type)
            result = handler(task.payload, lambda: self.tasks.cancellation_requested(task_id))
        except TaskCancelled:
            self.tasks.mark_cancelled(task)
            return {"cancelled": True}
        except Exception as exc:
            return self._handle_failure(task, exc)

        self.tasks.mark_succeeded(task, result)
        return result

    def _handle_failure(self, task: TaskModel, exc: Exception) -> dict[str, Any]:
        if task.attempts < task.max_attempts and task.cancel_requested_at is None:
            self.tasks.mark_queued_for_retry(task, exc)
            raise self.retry(exc=exc, countdown=2, max_retries=task.max_attempts - 1)

        self.tasks.mark_failed(task, exc)
        raise exc
