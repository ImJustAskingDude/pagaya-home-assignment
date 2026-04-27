from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import TaskStatus
from app.models.task import TaskModel
from app.repositories.filters import TaskFilter


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

    def store_celery_task_id(self, task: TaskModel, celery_task_id: str) -> TaskModel:
        task.celery_task_id = celery_task_id
        self.session.commit()
        self.session.refresh(task)
        return task

    def mark_dispatch_failed(self, task: TaskModel, exc: Exception) -> TaskModel:
        task.status = TaskStatus.FAILED.value
        task.error = f"Dispatch failed: {exc}"
        task.finished_at = datetime.now(timezone.utc)
        self.session.commit()
        return task

    def request_cancel(self, task: TaskModel) -> TaskModel:
        now = datetime.now(timezone.utc)
        task.cancel_requested_at = now
        if task.status == TaskStatus.QUEUED.value:
            task.status = TaskStatus.CANCELLED.value
            task.finished_at = now

        self.session.commit()
        self.session.refresh(task)
        return task

    def reset_for_retry(self, task: TaskModel) -> TaskModel:
        task.status = TaskStatus.QUEUED.value
        task.result = None
        task.error = None
        task.attempts = 0
        task.started_at = None
        task.finished_at = None
        task.cancel_requested_at = None
        task.celery_task_id = None
        self.session.commit()
        self.session.refresh(task)
        return task

    def mark_running(self, task: TaskModel) -> TaskModel:
        task.status = TaskStatus.RUNNING.value
        task.attempts += 1
        task.started_at = datetime.now(timezone.utc)
        task.finished_at = None
        task.error = None
        self.session.commit()
        return task

    def mark_cancelled(self, task: TaskModel) -> TaskModel:
        task.status = TaskStatus.CANCELLED.value
        task.finished_at = datetime.now(timezone.utc)
        self.session.commit()
        return task

    def mark_succeeded(self, task: TaskModel, result: dict[str, Any]) -> TaskModel:
        task.status = TaskStatus.SUCCEEDED.value
        task.result = result
        task.error = None
        task.finished_at = datetime.now(timezone.utc)
        self.session.commit()
        return task

    def mark_queued_for_retry(self, task: TaskModel, exc: Exception) -> TaskModel:
        task.error = str(exc)
        task.status = TaskStatus.QUEUED.value
        task.finished_at = None
        self.session.commit()
        return task

    def mark_failed(self, task: TaskModel, exc: Exception) -> TaskModel:
        task.error = str(exc)
        task.status = TaskStatus.FAILED.value
        task.finished_at = datetime.now(timezone.utc)
        self.session.commit()
        return task

    def cancellation_requested(self, task_id: int) -> bool:
        self.session.expire_all()
        task = self.session.get(TaskModel, task_id)
        return (
            task is None
            or task.status == TaskStatus.CANCELLED.value
            or task.cancel_requested_at is not None
        )
