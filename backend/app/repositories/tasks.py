from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import TaskStatus
from app.models.task import TaskModel
from app.repositories.filters import TaskFilter


class _UnsetValue:
    pass


_UNSET = _UnsetValue()


@dataclass(frozen=True)
class TaskStateUpdate:
    status: TaskStatus | _UnsetValue = _UNSET
    result: dict[str, Any] | None | _UnsetValue = _UNSET
    error: str | None | _UnsetValue = _UNSET
    attempts: int | _UnsetValue = _UNSET
    started_at: datetime | None | _UnsetValue = _UNSET
    finished_at: datetime | None | _UnsetValue = _UNSET
    cancel_requested_at: datetime | None | _UnsetValue = _UNSET
    celery_task_id: str | None | _UnsetValue = _UNSET

    @classmethod
    def store_celery_task_id(cls, celery_task_id: str) -> "TaskStateUpdate":
        return cls(celery_task_id=celery_task_id)

    @classmethod
    def dispatch_failed(cls, exc: Exception) -> "TaskStateUpdate":
        return cls(
            status=TaskStatus.FAILED,
            error=f"Dispatch failed: {exc}",
            finished_at=datetime.now(timezone.utc),
        )

    @classmethod
    def cancel_requested(cls) -> "TaskStateUpdate":
        return cls(cancel_requested_at=datetime.now(timezone.utc))

    @classmethod
    def queued_cancelled(cls) -> "TaskStateUpdate":
        now = datetime.now(timezone.utc)
        return cls(
            status=TaskStatus.CANCELLED,
            cancel_requested_at=now,
            finished_at=now,
        )

    @classmethod
    def retry_reset(cls) -> "TaskStateUpdate":
        return cls(
            status=TaskStatus.QUEUED,
            result=None,
            error=None,
            attempts=0,
            started_at=None,
            finished_at=None,
            cancel_requested_at=None,
            celery_task_id=None,
        )

    @classmethod
    def running(cls, attempts: int) -> "TaskStateUpdate":
        return cls(
            status=TaskStatus.RUNNING,
            attempts=attempts,
            started_at=datetime.now(timezone.utc),
            finished_at=None,
            error=None,
        )

    @classmethod
    def cancelled(cls) -> "TaskStateUpdate":
        return cls(status=TaskStatus.CANCELLED, finished_at=datetime.now(timezone.utc))

    @classmethod
    def succeeded(cls, result: dict[str, Any]) -> "TaskStateUpdate":
        return cls(
            status=TaskStatus.SUCCEEDED,
            result=result,
            error=None,
            finished_at=datetime.now(timezone.utc),
        )

    @classmethod
    def queued_for_retry(cls, exc: Exception) -> "TaskStateUpdate":
        return cls(
            status=TaskStatus.QUEUED,
            error=str(exc),
            finished_at=None,
        )

    @classmethod
    def failed(cls, exc: Exception) -> "TaskStateUpdate":
        return cls(
            status=TaskStatus.FAILED,
            error=str(exc),
            finished_at=datetime.now(timezone.utc),
        )

    def apply_to(self, task: TaskModel) -> None:
        if not isinstance(self.status, _UnsetValue):
            task.status = self.status.value
        if not isinstance(self.result, _UnsetValue):
            task.result = self.result
        if not isinstance(self.error, _UnsetValue):
            task.error = self.error
        if not isinstance(self.attempts, _UnsetValue):
            task.attempts = self.attempts
        if not isinstance(self.started_at, _UnsetValue):
            task.started_at = self.started_at
        if not isinstance(self.finished_at, _UnsetValue):
            task.finished_at = self.finished_at
        if not isinstance(self.cancel_requested_at, _UnsetValue):
            task.cancel_requested_at = self.cancel_requested_at
        if not isinstance(self.celery_task_id, _UnsetValue):
            task.celery_task_id = self.celery_task_id


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        offset: int,
        limit: int,
        filters: TaskFilter,
    ) -> tuple[list[TaskModel], int]:
        statement = filters.filter(select(TaskModel))
        count_statement = filters.filter(select(func.count()).select_from(TaskModel))

        total = self.session.scalar(count_statement) or 0
        items = self.session.scalars(filters.sort(statement).offset(offset).limit(limit)).all()
        return list(items), total

    def get(self, task_id: int) -> TaskModel | None:
        return self.session.get(TaskModel, task_id)

    def add(self, task: TaskModel) -> TaskModel:
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def delete(self, task: TaskModel) -> TaskModel:
        self.session.delete(task)
        self.session.commit()
        return task

    def update(
        self,
        task: TaskModel,
        state: TaskStateUpdate,
        *,
        refresh: bool = False,
    ) -> TaskModel:
        state.apply_to(task)
        self.session.commit()
        if refresh:
            self.session.refresh(task)
        return task

    def store_celery_task_id(self, task: TaskModel, celery_task_id: str) -> TaskModel:
        return self.update(
            task,
            TaskStateUpdate.store_celery_task_id(celery_task_id),
            refresh=True,
        )

    def mark_dispatch_failed(self, task: TaskModel, exc: Exception) -> TaskModel:
        return self.update(task, TaskStateUpdate.dispatch_failed(exc))

    def request_cancel(self, task: TaskModel) -> TaskModel:
        if task.status == TaskStatus.QUEUED.value:
            return self.update(task, TaskStateUpdate.queued_cancelled(), refresh=True)
        return self.update(task, TaskStateUpdate.cancel_requested(), refresh=True)

    def reset_for_retry(self, task: TaskModel) -> TaskModel:
        return self.update(task, TaskStateUpdate.retry_reset(), refresh=True)

    def mark_running(self, task: TaskModel) -> TaskModel:
        return self.update(task, TaskStateUpdate.running(attempts=task.attempts + 1))

    def mark_cancelled(self, task: TaskModel) -> TaskModel:
        return self.update(task, TaskStateUpdate.cancelled())

    def mark_succeeded(self, task: TaskModel, result: dict[str, Any]) -> TaskModel:
        return self.update(task, TaskStateUpdate.succeeded(result))

    def mark_queued_for_retry(self, task: TaskModel, exc: Exception) -> TaskModel:
        return self.update(task, TaskStateUpdate.queued_for_retry(exc))

    def mark_failed(self, task: TaskModel, exc: Exception) -> TaskModel:
        return self.update(task, TaskStateUpdate.failed(exc))

    def cancellation_requested(self, task_id: int) -> bool:
        self.session.expire_all()
        task = self.session.get(TaskModel, task_id)
        return (
            task is None
            or task.status == TaskStatus.CANCELLED.value
            or task.cancel_requested_at is not None
        )
