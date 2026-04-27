from collections.abc import Callable
from typing import Any, NoReturn, Protocol

from sqlalchemy.orm import Session

from app.core.enums import TaskStatus, TaskType
from app.models.task import TaskModel
from app.repositories.task_results import TaskResultRepository
from app.repositories.tasks import TaskRepository
from app.services.unit_of_work import UnitOfWork
from app.task_handlers.cancellation import TaskCancelled
from app.task_handlers.registry import get_handler


class RetryTask(Protocol):
    """Call shape used for Celery Task.retry."""

    def __call__(self, *, exc: Exception, countdown: int, max_retries: int) -> NoReturn: ...


class DispatchTask(Protocol):
    def enqueue(self, task_id: int) -> str: ...


class TaskExecutionService:
    def __init__(
        self,
        session: Session,
        retry: RetryTask,
        task_dispatcher: DispatchTask | None = None,
    ) -> None:
        self.retry = retry
        self.task_dispatcher = task_dispatcher
        self.unit_of_work = UnitOfWork(session)
        self.task_results = TaskResultRepository(session)
        self.tasks = TaskRepository(session)

    def execute(self, task_id: int) -> dict[str, Any]:
        task = self.tasks.get(task_id)
        if task is None:
            return {"ignored": True, "reason": "task_not_found"}
        if task.status == TaskStatus.CANCELLED.value or task.cancel_requested_at is not None:
            with self.unit_of_work:
                task.mark_cancelled()
                self.task_results.add_from_task(task)
                self.tasks.save(task)
            return {"cancelled": True}

        with self.unit_of_work:
            task.mark_running()
            self.tasks.save(task)

        try:
            is_cancel_requested = lambda: self.tasks.cancellation_requested(task_id)
            if task.type == TaskType.BATCH_FANOUT.value:
                result = self._execute_batch_fanout(task, is_cancel_requested)
            else:
                handler = get_handler(task.type)
                result = handler(task.payload, is_cancel_requested)
        except TaskCancelled:
            with self.unit_of_work:
                task.mark_cancelled()
                self.task_results.add_from_task(task)
                self.tasks.save(task)
            return {"cancelled": True}
        except Exception as exc:
            return self._handle_failure(task, exc)

        with self.unit_of_work:
            task.mark_succeeded(result)
            self.task_results.add_from_task(task)
            self.tasks.save(task)
        return result

    def _handle_failure(self, task: TaskModel, exc: Exception) -> dict[str, Any]:
        if task.attempts < task.max_attempts and task.cancel_requested_at is None:
            with self.unit_of_work:
                task.mark_queued_for_retry(exc)
                self.tasks.save(task)
            raise self.retry(exc=exc, countdown=2, max_retries=task.max_attempts - 1)

        with self.unit_of_work:
            task.mark_failed(exc)
            self.task_results.add_from_task(task)
            self.tasks.save(task)
        raise exc

    def _execute_batch_fanout(
        self,
        task: TaskModel,
        is_cancel_requested: Callable[[], bool],
    ) -> dict[str, Any]:
        if is_cancel_requested():
            raise TaskCancelled()

        child_count = int(task.payload["child_count"])
        message_prefix = str(task.payload["message_prefix"])
        child_max_attempts = int(task.payload.get("child_max_attempts", 1))
        dispatcher = self._task_dispatcher()
        children = []

        for index in range(1, child_count + 1):
            if is_cancel_requested():
                raise TaskCancelled()

            child = TaskModel(
                queue_id=task.queue_id,
                type=TaskType.ECHO.value,
                payload={"message": f"{message_prefix} {index}"},
                max_attempts=child_max_attempts,
            )

            with self.unit_of_work:
                self.tasks.add(child)

            try:
                celery_task_id = dispatcher.enqueue(child.id)
            except Exception as exc:
                with self.unit_of_work:
                    child.mark_dispatch_failed(exc)
                    self.task_results.add_from_task(child)
                    self.tasks.save(child)
                raise

            with self.unit_of_work:
                child.store_celery_task_id(celery_task_id)
                self.tasks.save(child)

            children.append(child)

        return {
            "child_count": child_count,
            "child_task_ids": [child.id for child in children],
        }

    def _task_dispatcher(self) -> DispatchTask:
        if self.task_dispatcher is not None:
            return self.task_dispatcher

        from app.services.dispatcher import dispatcher

        return dispatcher
