from typing import Any, NoReturn, Protocol

from sqlalchemy.orm import Session

from app.core.enums import TaskStatus
from app.models.task import TaskModel
from app.repositories.tasks import TaskRepository
from app.task_handlers.cancellation import TaskCancelled
from app.task_handlers.registry import get_handler


class RetryTask(Protocol):
    """Call shape used for Celery Task.retry."""

    def __call__(self, *, exc: Exception, countdown: int, max_retries: int) -> NoReturn: ...


class TaskExecutionService:
    def __init__(self, session: Session, retry: RetryTask) -> None:
        self.retry = retry
        self.tasks = TaskRepository(session)

    def execute(self, task_id: int) -> dict[str, Any]:
        task = self.tasks.get(task_id)
        if task is None:
            return {"ignored": True, "reason": "task_not_found"}
        if task.status == TaskStatus.CANCELLED.value or task.cancel_requested_at is not None:
            task.mark_cancelled()
            self.tasks.save(task)
            return {"cancelled": True}

        task.mark_running()
        self.tasks.save(task)

        try:
            handler = get_handler(task.type)
            result = handler(task.payload, lambda: self.tasks.cancellation_requested(task_id))
        except TaskCancelled:
            task.mark_cancelled()
            self.tasks.save(task)
            return {"cancelled": True}
        except Exception as exc:
            return self._handle_failure(task, exc)

        task.mark_succeeded(result)
        self.tasks.save(task)
        return result

    def _handle_failure(self, task: TaskModel, exc: Exception) -> dict[str, Any]:
        if task.attempts < task.max_attempts and task.cancel_requested_at is None:
            task.mark_queued_for_retry(exc)
            self.tasks.save(task)
            raise self.retry(exc=exc, countdown=2, max_retries=task.max_attempts - 1)

        task.mark_failed(exc)
        self.tasks.save(task)
        raise exc
